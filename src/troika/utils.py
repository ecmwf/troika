"""Various utilities"""

import getpass
import logging
import signal

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


def first_not_none(l):
    """Return the first element in `l` that is not None, if any

    >>> first_not_none(['a', 'b', 'c'])
    'a'
    >>> first_not_none([None, 1, 3])
    1
    >>> first_not_none([2, None, 6])
    2
    >>> first_not_none([None, None])
    >>> first_not_none([])
    """
    for x in l:
        if x is not None:
            return x
    return None


_parse_bool_sentinel = object()
def parse_bool(x, default=_parse_bool_sentinel):
    """Parse a boolean value

    Parameters
    ----------
    x: any
        Input value. Booleans are returned unchanged. True strings are "yes",
        "1", "true", and "on" (case insensitive). False strings are "no", "0",
        "false", "off" (case insensitive). Integer value 0 means False, 1
        means True. Any other value is considered invalid.
    default: any
        Return value in case of an invalid input

    Returns
    -------
    bool or type(default)

    Raises
    ------
    `ValueError`
        The input is invalid and no default is provided


    >>> all(parse_bool(x) for x in [True, "yes", "Yes", "true", "True", "on", "ON", "1", 1])
    True
    >>> any(parse_bool(x) for x in [False, "no", "No", "false", "False", "off", "OFF", "0", 0])
    False
    >>> parse_bool("maybe", default=False)
    False
    >>> parse_bool("maybe", default=True)
    True
    >>> parse_bool(None, default=False)
    False
    >>> parse_bool([], default=True)
    True
    >>> parse_bool(3, default=False)
    False
    >>> parse_bool("invalid")
    Traceback (most recent call last):
        ...
    ValueError: Cannot parse boolean 'invalid'
    """
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        x = x.lower()
        if x in ["no", "0", "false", "off"]:
            return False
        elif x in ["yes", "1", "true", "on"]:
            return True
    elif isinstance(x, int):
        if x == 0:
            return False
        elif x == 1:
            return True

    if default is not _parse_bool_sentinel:
        return default

    raise ValueError(f"Cannot parse boolean {x!r}")
