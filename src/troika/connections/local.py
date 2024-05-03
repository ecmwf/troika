"""Local connection class"""

import logging
import os
import pathlib
import shutil
import subprocess
from subprocess import DEVNULL, STDOUT

from .base import Connection

_logger = logging.getLogger(__name__)


class LocalConnection(Connection):
    """Connection to the local host"""

    def __init__(self, config, user):
        super().__init__(config, user)
        self.local_cwd = config.get("local_cwd", None)
        if self.local_cwd:
            self.local_cwd = pathlib.PurePath(self.local_cwd)

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def is_local(self):
        """See `Connection.is_local`"""
        return True

    def get_parent(self):
        """See `Connection.get_parent`"""
        return self

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
        if dryrun:
            _logger.info("Execute: %s", " ".join(repr(str(arg)) for arg in command))
            return
        if stdin is None:
            stdin = DEVNULL
        if stdout is None:
            stdout = DEVNULL
        if stderr is None:
            stderr = STDOUT
        if cwd is None:
            cwd = self.local_cwd
        elif self.local_cwd is not None:
            # Treat cwd relative to default if present
            cwd = self.local_cwd / cwd
        _logger.debug("Executing %s", " ".join(repr(str(arg)) for arg in command))
        proc = subprocess.Popen(
            command,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            text=text,
            encoding=encoding,
            errors=errors,
            start_new_session=detach,
            env=({**os.environ, **env} if env is not None else None),
            cwd=cwd,
        )
        _logger.debug("Child PID: %d", proc.pid)
        return proc

    def sendfile(self, src, dst, dryrun=False):
        """See `Connection.sendfile`"""
        if self.local_cwd:
            # If dst is relative, treat it relative to configured cwd
            dst = self.local_cwd / dst
        # but src is always relative to Troika process, not connection
        if not dryrun:
            shutil.copy(src, dst)
        else:
            _logger.info("Copying %r to %r", src, dst)

    def getfile(self, src, dst, dryrun=False):
        """See `Connection.getfile`"""
        if self.local_cwd:
            # If src is relative, treat it relative to configured cwd
            src = self.local_cwd / src
        # but dst is always relative to Troika process, not connection
        if not dryrun:
            shutil.copy(src, dst)
        else:
            _logger.info("Copying %r to %r", src, dst)
