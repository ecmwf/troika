"""Base connection class"""

import logging

from ..connection import PIPE

_logger = logging.getLogger(__name__)


class Connection:
    """Base connection class

    Parameters
    ----------
    config: dict
        Connection configuration
    """

    #: Value for the 'connection' key in the site configuration.
    #: If None, the name will be computed by turning the class name to
    #: lowercase and removing a trailing "connection" if present, e.g.
    #: ``FooConnection`` becomes ``foo``.
    __type_name__ = None

    def __init__(self, config, user):
        self.user = user

    def is_local(self):
        """Check whether the connection is local

        If the connection is local, local paths are valid through the connection
        """
        return False

    def get_parent(self):
        """Get the parent connection

        The parent connection can be used to interact with processes that have
        been created through the current connection.

        Returns
        -------
        Connection
            The parent connection
        """
        raise NotImplementedError

    def execute(
        self,
        command,
        stdin=None,
        stdout=None,
        stderr=None,
        text=False,
        encoding=None,
        errors=None,
        detach=False,
        env=None,
        cwd=None,
        dryrun=False,
    ):
        """Execute the given command on the host

        Parameters
        ----------
        command: list of str or path-like
            Command to execute, as a list of arguments
        stdin: None, PIPE or file-like
            Standard input, /dev/null if None
        stdout: None, PIPE or file-like
            Standard output, /dev/null if None
        stderr: None, PIPE, DEVNULL or file-like
            Standard error, same as stdout if None
        text: bool
            If True, open streams in text mode
        encoding: str or None
            Encoding to use for opening streams in text mode
        errors: str or None
            Error handling mode to use for decoding streams in text mode
        detach: bool
            If True, detach from the running command
        env: dict or None
            Extra variables to set in the command's environment
        cwd: path-like or None
            Override default working directory if not None
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        :py:class:`subprocess.Popen` object or None
            Local process object associated to the connection, if dryrun is False,
            else None
        """
        raise NotImplementedError

    def sendfile(self, src, dst, dryrun=False):
        """Copy the given file to the remote host

        Parameters
        ----------
        src: path-like
            Path to the file on the local host
        dst: path-like
            Path to the target directory or file on the remote host
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed
        """
        raise NotImplementedError

    def getfile(self, src, dst, dryrun=False):
        """Get the given file from the remote host

        Parameters
        ----------
        src: path-like
            Path to the file on the remote host
        dst: path-like
            Path to the target directory or file on the local host
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed
        """
        raise NotImplementedError

    def checkstatus(self, timeout=None, dryrun=False):
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
        proc = self.execute(
            ["true"], stdout=PIPE, stderr=PIPE, detach=False, dryrun=dryrun
        )
        if dryrun:
            return True
        proc_stdout, proc_stderr = proc.communicate()
        retcode = proc.returncode
        if proc.returncode == 0:
            log = _logger.debug
        else:
            log = _logger.error
        if proc_stdout:
            log("stdout checking connection:\n%s", proc_stdout.strip())
        if proc_stderr:
            log("stderr checking connection:\n%s", proc_stderr.strip())
        return retcode == 0
