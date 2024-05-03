"""Base controller class"""

import logging
import os
import pathlib
import shutil
import tempfile

from .. import ConfigurationError, InvocationError, RunError, hook, site
from ..directives import ALIASES, translators
from ..generator import Generator
from ..parser import DirectiveParser, MultiParser, ParseError, ShebangParser

_logger = logging.getLogger(__name__)


class Controller:
    """Main controller

    Parameters
    ----------
    config: :py:class:`troika.config.Config`
        Configuration
    args: :py:class:`argparse.Namespace`
        Command-line arguments
    logfile: path-like or None
        Path to the log file
    """

    __type_name__ = "base"

    def __init__(self, config, args, logfile):
        self.config = config
        self.args = args
        self.logfile = logfile
        self.site = None
        self.default_shebang = None
        self.unknown_directive = "warn"
        self.script_data = {}

    def __repr__(self):
        """Return a printable representation"""
        return "Controller"

    def submit(self, script, user, output, dryrun=False):
        """Process a 'submit' command

        The script and job ID are interpreted according to the site.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user:
            Remote user name
        output: path-like
            Path to the job output file
        dryrun: bool
            If True, do not submit, only report what would be done

        Returns
        -------
        int
            Return code (0 for success)
        """
        with self.action_context(parse_script=script) as context:
            pp_script = self.generate_script(script, user, output)
            hook.pre_submit(self.site, script, output, dryrun)
            self.site.submit(pp_script, user, output, dryrun)
        return context.status

    def monitor(self, script, user, output=None, jid=None, dryrun=False):
        """Process a 'monitor' command

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        output: path-like or None
            Path to the job output file
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not do anything, only report what would be done

        Returns
        -------
        int
            Return code (0 for success)
        """
        with self.action_context() as context:
            self.site.monitor(script, user, output, jid, dryrun)
        return context.status

    def kill(self, script, user, output=None, jid=None, dryrun=False):
        """Process a 'kill' command

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        output: path-like or None
            Path to the job output file
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not kill, only report what would be done

        Returns
        -------
        int
            Return code (0 for success)
        """
        with self.action_context() as context:
            jid, cancel_status = self.site.kill(script, user, output, jid, dryrun)
            hook.post_kill(self.site, script, output, jid, cancel_status, dryrun)
        return context.status

    def check_connection(self, timeout=None, dryrun=False):
        """Process a 'check-connection' command

        Parameters
        ----------
        timeout: int
            If set, consider the connection is not working if no response after
            this number of seconds
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        bool
            True if the connection is able to execute commands
        """
        with self.action_context() as context:
            working = self.site.check_connection(timeout=timeout, dryrun=dryrun)
            if not working:
                context.status = 1
        return context.status == 0

    def list_sites(self):
        """Process a 'list-sites' command

        Yields
        -------
        ``(name, type, connection)``
        """
        yield from site.list_sites(self.config)

    class ActionContext:
        def __init__(self, controller, *args, **kwargs):
            self._controller = controller
            self._controller.setup(*args, **kwargs)

        def __enter__(self):
            self.status = None
            return self

        def __exit__(self, exc_type, exc, traceback):
            if exc is None:
                if self.status is None:
                    self.status = 0
                swallow = False
            else:
                if self.status is None or self.status == 0:
                    self.status = 1
                if isinstance(exc, ConfigurationError):
                    _logger.critical("Configuration error: %s", exc)
                elif isinstance(exc, InvocationError):
                    _logger.critical("Invocation error: %s", exc)
                elif isinstance(exc, RunError):
                    _logger.critical("%s", exc)
                else:
                    _logger.error(
                        "Unhandled exception", exc_info=(exc_type, exc, traceback)
                    )
                swallow = True
            try:
                self._controller.teardown(self.status)
            except Exception as e:
                # An error during the at-exit hooks should _not_ be reported as
                # failure of the operation (e.g. submission failure)
                _logger.error("Exception during teardown/exit", exc_info=e)
            return swallow

    def action_context(self, *args, **kwargs):
        """Create a context manager for executing an action

        The arguments are passed to :py:meth:`setup` when entering the context manager
        """
        return self.ActionContext(self, *args, **kwargs)

    def setup(self, parse_script=None):
        """Set up the controller

        Parameters
        ----------
        parse_script: path-like, optional
            Parse this script
        """
        self.site = self._get_site()
        if parse_script is not None:
            self.parse_script(parse_script)
        hook.setup_hooks(self.config, self.args.site)
        res = hook.at_startup(self.args.action, self.site, self.args)
        if any(res):
            raise SystemExit(1)
        self.default_shebang = self.site.config.get("default_shebang", None)
        self.unknown_directive = self.site.config.get("unknown_directive", "warn")

    def teardown(self, sts=0):
        """Tear down the controller

        Parameters
        ----------
        sts: int
            Exit status
        """
        hook.at_exit(self.args.action, self.site, self.args, sts, self.logfile)

    def parse_script(self, script):
        """Parse the script

        Parameters
        ----------
        script: path-like
            Script to parse
        """
        dir_parser = DirectiveParser(aliases=ALIASES)
        parsers = [("directives", dir_parser)]
        native = self.site.get_native_parser()
        if native is not None:
            parsers.append(("native", native))
        parsers.append(("shebang", ShebangParser()))
        parser = MultiParser(parsers)
        body = self.run_parser(script, parser)
        self.script_data.update(parser.data)
        self.script_data["body"] = body
        dir_defines = getattr(self.args, "define", [])
        dir_overrides = dir_parser.parse_directive_args(dir_defines)
        self.script_data["directives"].update(dir_overrides)

    def run_parser(self, script, parser):
        """Run the parser on the script

        Parameters
        ----------
        script: path-like
            Path to the script
        parser: :py:class:`troika.parser.Parser`
            Parser to use

        Returns
        -------
        file-like
            Script body
        """
        script = pathlib.Path(script)
        stmp = tempfile.SpooledTemporaryFile(
            max_size=1024**3, mode="w+b", dir=script.parent, prefix=script.name
        )
        with open(script, "rb") as sin:
            try:
                for lineno, line in enumerate(sin, start=1):
                    drop = parser.feed(line)
                    if not drop:
                        stmp.write(line)
            except ParseError as e:
                raise ParseError(f"in {script!s}, line {lineno} {e!s}") from e
        stmp.seek(0)
        return stmp

    def generate_script(self, script, user, output):
        """Generate the post-processed script

        Parameters
        ----------
        script: path-like
            Path to the script
        user: str or None
            Remote user name
        output: path-like
            Path to the job output file

        Returns
        -------
        path-like
            Path to the post-processed script
        """
        if (
            self.default_shebang is not None
            and self.script_data.get("shebang", None) is None
        ):
            self.script_data["shebang"] = self.default_shebang.encode("utf-8")
        directive_prefix, directive_translate = self.site.get_directive_translation()
        generator = Generator(
            directive_prefix, directive_translate, self.unknown_directive
        )
        self.script_data["directives"]["output_file"] = os.fsencode(output)
        self.script_data = translators(self.script_data, self.config, self.site)
        return self.run_generator(script, generator)

    def run_generator(self, script, generator):
        """Generate the script file

        Parameters
        ----------
        script: path-like
            Path to the script
        generator: :py:class:`troika.generator.Generator`
            Generator to run

        Returns
        -------
        path-like
            Path to the generated script file
        """
        script = pathlib.Path(script)
        orig_script = script.with_suffix(script.suffix + ".orig")
        if orig_script.exists():
            _logger.warning(
                "Backup script file %r already exists, " + "overwriting",
                str(orig_script),
            )
        with tempfile.NamedTemporaryFile(
            mode="w+b", delete=False, dir=script.parent, prefix=script.name
        ) as sout:
            sout.writelines(generator.generate(self.script_data))
            for line in self.script_data["body"]:
                sout.write(line)
            new_script = pathlib.Path(sout.name)
        shutil.copymode(script, new_script)
        shutil.copy2(script, orig_script)
        new_script.replace(script)
        _logger.debug("Script generated. Original script saved to %r", str(orig_script))
        return script

    def _get_site(self):
        """Select the site and create the corresponding :py:class:`troika.sites.base.Site` instance"""
        return site.get_site(self.config, self.args.site, self.args.user)
