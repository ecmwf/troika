"""Script preprocessing utilities"""

import logging

from .hooks.base import Hook

_logger = logging.getLogger(__name__)


class PreprocessorHook(Hook):
    """Helper class to manage preprocessing hooks

    See `troika.hooks.base.Hook`. The only change is the behaviour of the
    `__call__` method::

        def __call__(self, script, *args, **kwargs):
            for proc in self.enabled_hooks:
                script = proc(script, *args, **kwargs)
            return script
    """

    def __call__(self, script, *args, **kwargs):
        for funcname, func in self._impl:
            _logger.debug("Calling preprocessor %s", funcname)
            script = func(script, *args, **kwargs)
        return script


@PreprocessorHook.declare
def preprocess(script_in, script_path, user, output):
    """Preprocessor

    Parameters
    ----------
    script_in: Iterable[bytes]
        Iterator over the lines of the script
    script_path: `pathlib.Path`
        Path to the original script
    user: str
        Remote user name
    output: path-like
        Path to the job output file

    Returns
    -------
    Iterable[str]
        Iterator over the lines of the preprocessed script
    """


@preprocess.register
def remove_top_blank_lines(sin, script, user, output):
    """Remove blank lines at the top of the script"""
    first = True
    for line in sin:
        if first:
            if line.isspace():
                continue
            first = False
        yield line
