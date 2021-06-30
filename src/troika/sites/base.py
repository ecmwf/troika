"""Base site class"""

import logging
import pathlib
import shutil
import tempfile

from .. import preprocess as pp

_logger = logging.getLogger(__name__)

class Site:
    """Base site class

    Parameters
    ----------
    config: dict
        Site configuration

    connection: `troika.connections.base.Connection`
        Connection object to interact with the site
    """

    #: Value for the 'type' key in the site configuration.
    #: If None, the name will be computed by turning the class name to
    #: lowercase and removing a trailing "site" if present, e.g. ``FooSite``
    #: becomes ``foo``.
    __type_name__ = None

    def __init__(self, config, connection):
        self._connection = connection
        self._kill_sequence = config.get('kill_sequence', None)

    def preprocess(self, script, user, output):
        """Preprocess a job script

        The script, output and user are interpreted according to the site.

        Parameters
        ----------
        script: path-like
            Path to the job script
        output: path-like
            Path to the job output file
        user:
            Remote user name

        Returns
        -------
        path-like:
            Path to the preprocessed script
        """
        script = pathlib.Path(script)
        orig_script = script.with_suffix(script.suffix + ".orig")
        if orig_script.exists():
            _logger.warning("Backup script file %r already exists, " +
                "overwriting", str(orig_script))
        with script.open(mode="r") as sin, \
                tempfile.NamedTemporaryFile(mode='w+', delete=False,
                    dir=script.parent, prefix=script.name) as sout:
            sin_pp = pp.preprocess(sin, script, user, output)
            sout.writelines(sin_pp)
            new_script = pathlib.Path(sout.name)
        shutil.copymode(script, new_script)
        shutil.copy2(script, orig_script)
        new_script.replace(script)
        _logger.debug("Preprocessing done. Original script saved to %r",
            str(orig_script))
        return script

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

    def monitor(self, script, user, jid=None, dryrun=False):
        """Kill a submitted job

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
        raise NotImplementedError()

    def kill(self, script, user, jid=None, dryrun=False):
        """Kill a submitted or running job

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
