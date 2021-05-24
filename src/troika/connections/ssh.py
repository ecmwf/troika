"""SSH connection class"""

from .base import Connection
from .local import LocalConnection

from .. import RunError


class SSHConnection(Connection):
    """Connection to a remote host via SSH"""

    def __init__(self, config, user):
        super().__init__(config, user)
        self.parent = LocalConnection({}, user)
        self.ssh = config.get('ssh_command', 'ssh')
        self.scp = config.get('scp_command', 'scp')
        self.host = config['host']

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self.host!r}, user={self.user!r})"

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            detach=False, dryrun=False):
        """See `Connection.execute`"""
        ssh_args = [self.ssh, '-v', '-o', 'StrictHostKeyChecking=no',
            '-l', self.user, self.host]
        args = ssh_args + command
        return self.parent.execute(args, stdin=stdin, stdout=stdout,
            stderr=stderr, detach=detach, dryrun=dryrun)

    def sendfile(self, src, dst, dryrun=False):
        """See `Connection.sendfile`"""
        scp_args = [self.scp, '-v', '-o', 'StrictHostKeyChecking=no', src,
            f"{self.user}@{self.host}:{dst}"]
        proc = self.parent.execute(scp_args, dryrun=dryrun)
        if dryrun:
            return
        retcode = proc.wait()
        if retcode != 0:
            msg = "Copy "
            if retcode > 0:
                msg += f"failed with exit code {retcode}"
            else:
                msg += f"terminated by signal {-retcode}"
            raise RunError(msg)
