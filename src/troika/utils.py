"""Various utilities"""

import getpass
import signal

from posix_ipc import Semaphore, O_CREAT

from . import RunError


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
    """
    def __init__(self, limit=0, user=None, mode=0o600):
        if user is None:
            user = getpass.getuser()
        self.sem = None
        if limit > 0:
            self.sem = Semaphore(f"/troika:{user}", flags=O_CREAT, mode=mode, initial_value=limit)

    def __enter__(self):
        if self.sem is not None:
            return self.sem.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.sem is not None:
            return self.sem.__exit__(exc_type, exc_value, traceback)
