"""Base site class"""

import logging
import os
import pathlib

from .. import ConfigurationError, generator
from ..connection import PIPE
from ..utils import check_retcode, command_as_list, normalise_signal

_logger = logging.getLogger(__name__)


class Site:
    """Base site class

    Parameters
    ----------
    config: dict
        Site configuration

    connection: :py:class:`troika.connections.base.Connection`
        Connection object to interact with the site

    global_config: :py:class:`troika.config.Config`
        Global configuration
    """

    #: Value for the 'type' key in the site configuration.
    #: If None, the name will be computed by turning the class name to
    #: lowercase and removing a trailing "site" if present, e.g. ``FooSite``
    #: becomes ``foo``.
    __type_name__ = None

    #: Prefix for the generated directives, e.g. ``b"#SBATCH "``. If ``None``,
    #: no directives will be generated
    directive_prefix = None

    #: Directive translation table (``str`` -> ``bytes``). Values are formatted
    #: using the ``%`` operator
    directive_translate = {}

    def __init__(self, config, connection, global_config):
        self.config = config
        self._connection = connection
        try:
            self._kill_sequence = [
                (wait, normalise_signal(sig))
                for wait, sig in config.get("kill_sequence", [])
            ]
        except (TypeError, ValueError) as e:
            raise ConfigurationError(f"Invalid kill sequence: {e!s}")

    def submit(self, script, user, output, dryrun=False):
        """Submit a job

        The script and output path are interpreted according to the site.

        Parameters
        ----------
        script: path-like
            Path to the job script
        output: path-like
            Path to the output file
        user: str
            Remote user name
        dryrun: bool
            If True, do not submit, only report what would be done
        """
        raise NotImplementedError()

    def monitor(self, script, user, output=None, jid=None, dryrun=False):
        """Kill a submitted job

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        output: path-like or None
            Path to the output file
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not do anything, only report what would be done
        """
        raise NotImplementedError()

    def kill(self, script, user, output=None, jid=None, dryrun=False):
        """Kill a submitted or running job

        The script and job ID are interpreted according to the site.
        If no job ID is provided, it will be inferred.

        Parameters
        ----------
        script: path-like
            Path to the job script
        user: str
            Remote user name
        output: path-like or None
            Path to the output file
        jid: str or None
            Job ID
        dryrun: bool
            If True, do not kill, only report what would be done

        Returns
        -------
        tuple:
            [0]
                The job ID of the killed job
            [1]
                CANCELLED:
                    the job was cancelled before it started
                KILLED:
                    the job was killed while running without a
                    catchable signal allowing it to clean up or
                    report its demise
                TERMINATED:
                    the job was sent a catchable signal while running
                    and is expected to clean up and report its own
                    demise if necessary
                VANISHED:
                    the job has disappeared so no further attempt
                    could be made to kill it
        """
        raise NotImplementedError()

    def check_connection(self, timeout=None, dryrun=False):
        """Check whether the connection is working

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
        return self._connection.checkstatus(timeout=timeout, dryrun=dryrun)

    def create_output_dir(self, output, dryrun=False):
        """Create the output directory for a job to be submitted

        Parameters
        ----------
        output: path-like
            Path to the output file
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        :py:class:`pathlib.PurePath`
            Path to the newly created directory
        """
        out_dir = pathlib.PurePath(output).parent
        pmkdir_command = command_as_list(
            self.config.get("pmkdir_command", ["mkdir", "-p"])
        )
        proc = self._connection.execute(
            pmkdir_command + [out_dir], stdout=PIPE, stderr=PIPE, dryrun=dryrun
        )
        if dryrun:
            return out_dir
        proc_stdout, proc_stderr = proc.communicate()
        if proc.returncode != 0:
            if proc_stdout:
                _logger.error("%s stdout:\n%s", pmkdir_command[0], proc_stdout.strip())
            if proc_stderr:
                _logger.error("%s stderr:\n%s", pmkdir_command[0], proc_stderr.strip())
            check_retcode(proc.returncode, what="Output directory creation")
        else:
            if proc_stdout:
                _logger.debug("%s stdout:\n%s", pmkdir_command[0], proc_stdout.strip())
            if proc_stderr:
                _logger.debug("%s stderr:\n%s", pmkdir_command[0], proc_stderr.strip())
        return out_dir

    def get_native_parser(self):
        """Create a :py:class:`troika.parser.Parser` for native directives

        Returns
        -------
        :py:class:`troika.parser.Parser` or None
            Directive parser, if any
        """
        return None

    def get_directive_translation(self):
        """Construct the translation params

        Returns
        -------
        tuple
            ``(directive_prefix, directive_translate)``, updated with the
            configuration overrides
        """
        prefix = self.config.get("directive_prefix", self.directive_prefix)
        translate = self.directive_translate.copy()
        for name, fmt in self.config.get("directive_translate", {}).items():
            if fmt is None:
                translate[name] = generator.ignore
            else:
                translate[name] = fmt.encode("utf-8")
        return (prefix, translate)

    def remove_previous_output(self, output, dryrun=False):
        """Remove previous output file if existing.

        Parameters
        ----------
        output: path-like
            Path to the output file
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        """
        if os.path.exists(output):
            if dryrun:
                _logger.info("removing:\n%s", output)
            else:
                os.remove(output)
