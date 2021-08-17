"""Various utilities"""

import getpass
import logging
import signal

import posix_ipc as ipc

from . import RunError

_logger = logging.getLogger(__name__)


def signal_name(sig):
    """Get the usual SIG* name associated to the given signal number

    >>> signal_name(2)
    'SIGINT'
    >>> signal_name(9)
    'SIGKILL'
    >>> signal_name(15)
    'SIGTERM'
    >>> signal_name(0)
    Traceback (most recent call last):
        ...
    KeyError: 0
    """
    match = [s for s in signal.Signals if s.value == int(sig)]
    if len(match) != 1:
        raise KeyError(sig)
    return match[0].name


def check_retcode(retcode, what="Command", suffix=""):
    """Check a return code and raise an error if needed

    Parameters
    ----------
    retcode: int
        Return code, see `subprocess.Popen.returncode`
    what: str
        Description of what was run
    suffix: str
        Extra content to append to the error message

    Raises
    ------
    `troika.RunError`
        The return code was nonzero


    >>> check_retcode(0)
    >>> check_retcode(1)
    Traceback (most recent call last):
        ...
    troika.RunError: Command failed with exit code 1
    >>> check_retcode(-6)
    Traceback (most recent call last):
        ...
    troika.RunError: Command terminated by signal 6
    """
    if retcode != 0:
        msg = what
        if retcode > 0:
            msg += f" failed with exit code {retcode}"
        else:
            msg += f" terminated by signal {-retcode}"
        msg += suffix
        raise RunError(msg)


class ConcurrencyLimit:
    """Limit the number of concurrent instances of the program

    To be used as a context manager.

    Parameters
    ----------
    limit: int, default: 0
        Maximum number of instances (0 means unlimited)
    user: str, default: current user
        Bind the limit to the given user
    mode: int, default: 0o600
        Permissions of the underlying semaphore
    timeout: int or None, default: None
        If not None, wait for that many seconds before failing. A value of 0
        effectively means that the `__enter__` method will fail immediately if
        the limit is reached
    """
    def __init__(self, limit=0, user=None, mode=0o600, timeout=None):
        if user is None:
            user = getpass.getuser()
        self.timeout = timeout
        if timeout is not None and timeout > 0 and not ipc.SEMAPHORE_TIMEOUT_SUPPORTED:
            _logger.warn("Concurrency limit timeout not supported on this platform")
        self.sem = None
        if limit > 0:
            self.sem = ipc.Semaphore(f"/troika:{user}:{limit}",
                flags=ipc.O_CREAT, mode=mode, initial_value=limit)

    def __enter__(self):
        if self.sem is not None:
            try:
                return self.sem.acquire(self.timeout)
            except ipc.BusyError:
                raise RunError("Too many processes running simultaneously")

    def __exit__(self, exc_type, exc_value, traceback):
        if self.sem is not None:
            self.sem.release()
            self.sem.close()
