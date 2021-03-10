"""Various utilities"""

import os

def check_status(sts):
    """Check the return value of `os.waitpid`

    Parameters
    ----------
    sts: int
        Status as returned by `os.waitpid`

    Returns
    -------
    ret: int
        If ``ret >= 0``: exit code, otherwise ``-ret`` is the signal number

    Raises
    ------
    ValueError
        When ``sts`` is invalid
    """
    if hasattr(os, "waitstatus_to_exitcode"):  # Python >=3.9
        return os.waitstatus_to_exitcode(sts)
    if os.WIFSIGNALED(sts):
        return -os.WTERMSIG(sts)
    if os.WIFEXITED(sts):
        return os.WEXITSTATUS(sts)
    raise ValueError(f"invalid wait status: {sts}")
