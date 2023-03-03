"""SSH connection class"""

import pathlib
import shlex

from .base import Connection
from .local import LocalConnection

from ..utils import check_retcode, parse_bool


class SSHConnection(Connection):
    """Connection to a remote host via SSH"""

    def __init__(self, config, user):
        super().__init__(config, user)
        self.parent = LocalConnection(config, user)
        self.ssh = config.get('ssh_command', 'ssh')
        self.scp = config.get('scp_command', 'scp')
        self.ssh_options = config.get('ssh_options', [])
        if parse_bool(config.get('ssh_verbose', False)):
            self.ssh_options.append('-v')
        strict_host_key_checking = parse_bool(config.get('ssh_strict_host_key_checking', False))
        if strict_host_key_checking is not None:
            self.ssh_options.append(f'-oStrictHostKeyChecking={"yes" if strict_host_key_checking else "no"}')
        connect_timeout = config.get('ssh_connect_timeout', None)
        if connect_timeout is not None:
            self.ssh_options.append(f'-oConnectTimeout={connect_timeout}')
        self.host = config['host']
        if self.user is None:
            self.user = config.get('user', None)
        self.ssh_cwd = config.get('ssh_cwd', None)
        if self.ssh_cwd:
            self.ssh_cwd = pathlib.PurePath(self.ssh_cwd)

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self.host!r}, user={self.user!r})"

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            text=False, encoding=None, errors=None, detach=False,
            env=None, cwd=None, dryrun=False):
        """See `Connection.execute`"""
        args = [self.ssh] + self.ssh_options
        if self.user is None:
            args.append(f"{self.host}")
        else:
            args.append(f"{self.user}@{self.host}")
        if cwd is None:
            cwd = self.ssh_cwd
        elif self.ssh_cwd is not None:
            # Treat cwd relative to default if present
            cwd = self.ssh_cwd / cwd
        if cwd is not None:
            args += [ 'cd', shlex.quote(str(cwd)), '&&' ]
        if env is not None:
            args += [ f'{shlex.quote(k)}={shlex.quote(v)}' for k,v in env.items() ]
        args += [ shlex.quote(str(arg)) for arg in command ]
        return self.parent.execute(args, stdin=stdin, stdout=stdout,
            stderr=stderr, text=text, encoding=encoding, errors=errors,
            detach=detach, dryrun=dryrun)

    def sendfile(self, src, dst, dryrun=False):
        """See `Connection.sendfile`"""
        if self.parent.local_cwd is not None:
            # src is always relative to Troika process, not underlying LocalConnection
            src = Path(src).absolute()
        if self.ssh_cwd:
            # If dst is relative, treat it relative to configured cwd
            dst = self.ssh_cwd / dst
        scp_args = [self.scp] + self.ssh_options + [src]
        if self.user is None:
            scp_args.append(f"{self.host}:{dst}")
        else:
            scp_args.append(f"{self.user}@{self.host}:{dst}")
        proc = self.parent.execute(scp_args, dryrun=dryrun)
        if dryrun:
            return
        retcode = proc.wait()
        check_retcode(retcode, what="Copy")
