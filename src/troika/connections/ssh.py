"""SSH connection class"""

import logging
import pathlib
import shlex

from ..connection import PIPE
from ..utils import check_retcode, parse_bool
from .base import Connection
from .local import LocalConnection

_logger = logging.getLogger(__name__)


class SSHConnection(Connection):
    """Connection to a remote host via SSH"""

    def __init__(self, config, user):
        super().__init__(config, user)
        self.parent = LocalConnection(config, user)
        self.ssh = config.get("ssh_command", "ssh")
        self.scp = config.get("scp_command", "scp")
        self.ssh_options = config.get("ssh_options", [])
        self.scp_options = config.get("scp_options", self.ssh_options.copy())
        if parse_bool(config.get("ssh_verbose", False)):
            self.ssh_options.append("-v")
            self.scp_options.append("-v")
        strict_host_key_checking = parse_bool(
            config.get("ssh_strict_host_key_checking", False)
        )
        if strict_host_key_checking is not None:
            self.ssh_options.append(
                f'-oStrictHostKeyChecking={"yes" if strict_host_key_checking else "no"}'
            )
            self.scp_options.append(
                f'-oStrictHostKeyChecking={"yes" if strict_host_key_checking else "no"}'
            )
        connect_timeout = config.get("ssh_connect_timeout", None)
        if connect_timeout is not None:
            self.ssh_options.append(f"-oConnectTimeout={connect_timeout}")
            self.scp_options.append(f"-oConnectTimeout={connect_timeout}")
        self.host = config["host"]
        if self.user is None:
            self.user = config.get("user", None)
        self.remote_cwd = config.get("remote_cwd", None)
        if self.remote_cwd:
            self.remote_cwd = pathlib.PurePath(self.remote_cwd)

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self.host!r}, user={self.user!r})"

    def get_parent(self):
        """See `Connection.get_parent`"""
        return self.parent

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
        """See `Connection.execute`"""
        args = [self.ssh] + self.ssh_options
        if self.user is None:
            args.append(f"{self.host}")
        else:
            args.append(f"{self.user}@{self.host}")
        if cwd is None:
            cwd = self.remote_cwd
        elif self.remote_cwd is not None:
            # Treat cwd relative to default if present
            cwd = self.remote_cwd / cwd
        if cwd is not None:
            args += ["cd", shlex.quote(str(cwd)), "&&"]
        if env is not None:
            args += [f"{shlex.quote(k)}={shlex.quote(v)}" for k, v in env.items()]
        args += [shlex.quote(str(arg)) for arg in command]
        return self.parent.execute(
            args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            text=text,
            encoding=encoding,
            errors=errors,
            detach=detach,
            dryrun=dryrun,
        )

    def sendfile(self, src, dst, dryrun=False):
        """See `Connection.sendfile`"""
        if self.parent.local_cwd is not None:
            # src is always relative to Troika process, not underlying LocalConnection
            src = pathlib.Path(src).absolute()
        if self.remote_cwd:
            # If dst is relative, treat it relative to configured cwd
            dst = self.remote_cwd / dst
        scp_args = [self.scp] + self.scp_options + [src]
        if self.user is None:
            scp_args.append(f"{self.host}:{dst}")
        else:
            scp_args.append(f"{self.user}@{self.host}:{dst}")
        proc = self.parent.execute(scp_args, stdout=PIPE, stderr=PIPE, dryrun=dryrun)
        if dryrun:
            return
        proc_stdout, proc_stderr = proc.communicate()
        proc_stdout = proc_stdout.strip()
        proc_stderr = proc_stderr.strip()
        retcode = proc.wait()
        if proc_stdout:
            _logger.debug("scp output: %s", proc_stdout)
        if retcode != 0:
            if proc_stderr:
                _logger.error("scp error: %s", proc_stderr)
        else:
            if proc_stderr:
                _logger.debug("scp error output: %s", proc_stderr)
        check_retcode(retcode, what="Copy")

    def getfile(self, src, dst, dryrun=False):
        """See `Connection.getfile`"""
        if self.remote_cwd:
            # If src is relative, treat it relative to configured cwd
            src = self.remote_cwd / src
        if self.parent.local_cwd is not None:
            # dst is always relative to Troika process, not underlying LocalConnection
            dst = pathlib.Path(dst).absolute()
        scp_args = [self.scp] + self.scp_options
        if self.user is None:
            scp_args.append(f"{self.host}:{src}")
        else:
            scp_args.append(f"{self.user}@{self.host}:{src}")
        scp_args.append(dst)
        proc = self.parent.execute(scp_args, stdout=PIPE, stderr=PIPE, dryrun=dryrun)
        if dryrun:
            return
        proc_stdout, proc_stderr = proc.communicate()
        proc_stdout = proc_stdout.strip()
        proc_stderr = proc_stderr.strip()
        retcode = proc.wait()
        if proc_stdout:
            _logger.debug("scp output: %s", proc_stdout)
        if retcode != 0:
            if proc_stderr:
                _logger.error("scp error: %s", proc_stderr)
        else:
            if proc_stderr:
                _logger.debug("scp error output: %s", proc_stderr)
        check_retcode(retcode, what="Copy")
