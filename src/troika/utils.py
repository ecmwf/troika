"""Various utilities"""

import logging
import signal

from . import RunError

_logger = logging.getLogger(__name__)


def normalise_signal(sig):
    """Get the `signal.Signals` value associated with the given signal

    >>> normalise_signal(2)
    <Signals.SIGINT: 2>
    >>> normalise_signal('KILL')
    <Signals.SIGKILL: 9>
    >>> normalise_signal('SIGTERM')
    <Signals.SIGTERM: 15>
    >>> normalise_signal('NOTASIGNAL')
    Traceback (most recent call last):
        ...
    ValueError: Invalid signal: 'NOTASIGNAL'
    >>> normalise_signal(-3)
    Traceback (most recent call last):
        ...
    ValueError: Invalid signal: -3
    """
    if isinstance(sig, signal.Signals):
        return sig
    elif isinstance(sig, str):
        name = sig.upper()
        if not name.startswith("SIG"):
            name = "SIG" + name
        match = [s for s in signal.Signals if s.name == name]
        if len(match) == 1:
            return match[0]
    elif isinstance(sig, int):
        match = [s for s in signal.Signals if s.value == int(sig)]
        if len(match) == 1:
            return match[0]
    raise ValueError(f"Invalid signal: {sig!r}")


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


def first_not_none(lst):
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
    for x in lst:
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
    >>> all(parse_bool(x) for x in [b"yes", b"Yes", b"true", b"True", b"on", b"ON", "1"])
    True
    >>> any(parse_bool(x) for x in [b"no", b"No", b"false", b"False", b"off", b"OFF", b"0"])
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
    if isinstance(x, bytes):
        x = x.decode("ascii", "replace")
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


def command_as_list(x):
    """Return the given command as a list

    >>> command_as_list("foo")
    ['foo']
    >>> command_as_list("spaces not split")
    ['spaces not split']
    >>> command_as_list(b"bytes")
    [b'bytes']
    >>> command_as_list(["prg", "arg1", "arg2"])
    ['prg', 'arg1', 'arg2']
    """
    if isinstance(x, (str, bytes)):
        return [x]
    return list(x)
