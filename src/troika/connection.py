"""Abstraction of the way to connect to a host"""

import logging
import subprocess
from subprocess import DEVNULL, STDOUT, PIPE

from . import ConfigurationError

_logger = logging.getLogger(__name__)


class Connection:
    """Base connection class

    Parameters
    ----------
    config: dict
        Connection configuration
    """

    def __init__(self, config, user):
        self.user = user

    def is_local(self):
        """Check whether the connection is local

        If the connection is local, local paths are valid through the connection
        """
        return False

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            detach=False, dryrun=False):
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
        detach: bool
            If True, detach from the running command
        dryrun: bool
            If True, do not do anything but print the command that would be
            executed

        Returns
        -------
        int or None
            Local process ID associated to the connection, if dryrun is False,
            else None
        """
        raise NotImplementedError


class LocalConnection(Connection):
    """Connection to the local host"""

    def __init__(self, config, user):
        super().__init__(config, user)

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def is_local(self):
        """See `troika.connection.Connection.is_local"""
        return True

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            detach=False, dryrun=False):
        """See `troika.connection.Connection.execute"""
        if dryrun:
            _logger.info("Execute: %s", " ".join(repr(str(arg)) for arg in command))
            return
        if stdin is None:
            stdin = DEVNULL
        if stdout is None:
            stdout = DEVNULL
        if stderr is None:
            stderr = STDOUT
        _logger.debug("Executing %s", " ".join(repr(str(arg)) for arg in command))
        proc = subprocess.Popen(command, stdin=stdin, stdout=stdout,
            stderr=stderr, start_new_session=detach)
        _logger.debug("Child PID: %d", proc.pid)
        return proc.pid


class SSHConnection(Connection):
    """Connection to a remote host via SSH"""

    def __init__(self, config, user):
        super().__init__(config, user)
        self.parent = LocalConnection({}, user)
        self.ssh = config.get('ssh_command', 'ssh')
        self.host = config['host']

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self.host!r}, user={self.user!r})"

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            detach=False, dryrun=False):
        """See `troika.connection.Connection.execute"""
        ssh_args = [self.ssh, '-v', '-o', 'StrictHostKeyChecking=no',
            '-l', self.user, self.host]
        args = ssh_args + command
        return self.parent.execute(args, stdin=stdin, stdout=stdout,
            stderr=stderr, detach=detach, dryrun=dryrun)


_CONNECTIONS = {
    "local": LocalConnection,
    "ssh": SSHConnection
}


def get_connection(name, config, user):
    _logger.debug("Available connection types: %s", ", ".join(_CONNECTIONS.keys()))

    try:
       cls = _CONNECTIONS[name]
    except KeyError:
        raise ConfigurationError(f"Unknown connection {name!r}")

    conn = cls(config, user)
    _logger.debug("Created connection %r", conn)
    return conn