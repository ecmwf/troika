"""Base connection class"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import IO, TYPE_CHECKING, Any, ClassVar

from ..connection import PIPE

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from os import PathLike
    from subprocess import Popen

    #: Something that can be interpreted as a filesystem path.
    StrPath = str | PathLike[str]
    #: A concrete redirection target accepted by :py:class:`subprocess.Popen`
    #: (``None`` -- the default -- is spelled ``Redirect | None`` at each use).
    Redirect = int | IO[Any]

_logger = logging.getLogger(__name__)


class Connection(ABC):
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
    __type_name__: ClassVar[str | None] = None

    def __init__(self, config: Mapping[str, Any], user: str | None) -> None:
        self.user = user

    def is_local(self) -> bool:
        """Check whether the connection is local

        If the connection is local, local paths are valid through the connection
        """
        return False

    @abstractmethod
    def get_parent(self) -> Connection:
        """Get the parent connection

        The parent connection can be used to interact with processes that have
        been created through the current connection.

        Returns
        -------
        Connection
            The parent connection
        """
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        command: Sequence[str],
        stdin: Redirect | None = None,
        stdout: Redirect | None = None,
        stderr: Redirect | None = None,
        text: bool = False,
        encoding: str | None = None,
        errors: str | None = None,
        detach: bool = False,
        env: Mapping[str, str] | None = None,
        cwd: StrPath | None = None,
        dryrun: bool = False,
    ) -> Popen[Any] | None:
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

    @abstractmethod
    def sendfile(self, src: StrPath, dst: StrPath, dryrun: bool = False) -> None:
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

    @abstractmethod
    def getfile(self, src: StrPath, dst: StrPath, dryrun: bool = False) -> None:
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

    def checkstatus(self, timeout: int | None = None, dryrun: bool = False) -> bool:
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
        proc = self.execute(["true"], stdout=PIPE, stderr=PIPE, detach=False, dryrun=dryrun)
        if dryrun:
            return True
        assert proc is not None  # execute only returns None when dryrun is True
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
