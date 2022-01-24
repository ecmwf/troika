"""Base controller class"""

import pathlib
import tempfile

from .. import hook
from ..parser import DirectiveParser, MultiParser, ParseError
from .. import site


class Controller:
    """Main controller

    Parameters
    ----------
    """

    __type_name__ = "base"

    def __init__(self, config, args, logfile):
        self.config = config
        self.args = args
        self.logfile = logfile
        self.site = None
        self.script_data = {}

    def __repr__(self):
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
        """
        self.setup(parse_script=script)
        pp_script = self.site.preprocess(script, user, output)
        hook.pre_submit(self.site, output, dryrun)
        self.site.submit(pp_script, user, output, dryrun)
        self.teardown()

    def monitor(self, script, user, jid=None, dryrun=False):
        """Process a 'monitor' command

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not do anything, only report what would be done
        """
        self.setup()
        self.site.monitor(script, user, jid, dryrun)
        self.teardown()

    def kill(self, script, user, jid=None, dryrun=False):
        """Process a 'kill' command

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not kill, only report what would be done
        """
        self.setup()
        self.site.kill(script, user, jid, dryrun)
        self.teardown()

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
        self.setup()
        working = self.site.check_connection(timeout=timeout, dryrun=dryrun)
        self.teardown(0 if working else 1)
        return working

    def list_sites(self):
        """Process a 'list-sites' command

        Yields
        -------
        ``(name, type, connection)``
        """
        yield from site.list_sites(self.config)

    def setup(self, parse_script=None):
        if parse_script is not None:
            self.parse_script(parse_script)
        self.site = self._get_site()
        hook.setup_hooks(self.config, self.args.site)
        res = hook.at_startup(self.args.action, self.site, self.args)
        if any(res):
            raise SystemExit(1)

    def teardown(self, sts=0):
        hook.at_exit(self.args.action, self.site, self.args, sts, self.logfile)

    def parse_script(self, script):
        parsers = [('directives', DirectiveParser())]
        native = self.site.get_native_parser()
        if native is not None:
            parsers.append(('native', native))
        parsers.append(('shebang', ShebangParser()))
        parser = MultiParser(parsers)
        body = self.run_parser(script, parser)
        self.script_data.update(parser.data)
        self.script_data['body'] = body

    def run_parser(self, script, parser):
        script = pathlib.Path(script)
        stmp = tempfile.SpooledTemporaryFile(max_size=1024**3, mode='w+b',
            dir=script.parent, prefix=script.name)
        with open(script, 'rb') as sin:
            try:
                for lineno, line in enumerate(sin, start=1):
                    drop = parser.feed(line)
                    if not drop:
                        stmp.write(line)
            except ParseError as e:
                raise ParseError(f"in {script!s}, line {lineno} {e!s}") from e
        stmp.seek(0)
        return stmp

    def _get_site(self):
        return site.get_site(self.config, self.args.site, self.args.user)
