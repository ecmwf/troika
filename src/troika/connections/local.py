"""Local connection class"""

import logging
import os
import shutil
import subprocess
from subprocess import DEVNULL, STDOUT

from .base import Connection

_logger = logging.getLogger(__name__)


class LocalConnection(Connection):
    """Connection to the local host"""

    def __init__(self, config, user):
        super().__init__(config, user)

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def is_local(self):
        """See `Connection.is_local`"""
        return True

    def execute(self, command, stdin=None, stdout=None, stderr=None,
            text=False, encoding=None, errors=None, detach=False,
            env=None, dryrun=False):
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
        _logger.debug("Executing %s", " ".join(repr(str(arg)) for arg in command))
        proc = subprocess.Popen(command, stdin=stdin, stdout=stdout,
            stderr=stderr, text=text, encoding=encoding, errors=errors,
            start_new_session=detach,
            env=({**os.environ, **env} if env is not None else None))
        _logger.debug("Child PID: %d", proc.pid)
        return proc

    def sendfile(self, src, dst, dryrun=False):
        """See `Connection.sendfile`"""
        if not dryrun:
            shutil.copy(src, dst)
        else:
            _logger.info("Copying %r to %r", src, dst)
