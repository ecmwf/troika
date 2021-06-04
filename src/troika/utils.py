"""Various utilities"""

import signal


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
