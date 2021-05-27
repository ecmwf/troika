"""Script preprocessing utilities"""

import logging
import pathlib
import shutil
import tempfile

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

    registered_hooks = {}  # store preprocessors separately

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
    script_in: Iterable[str]
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


class PreprocessMixin:
    """Mixin to be added to a site to enable simple preprocessing

    Example::

        class MySite(PreprocessMixin, Site):
            preprocessors = [pp1, pp2, ...]
            ...

    The original script will be backed up at ``<script>.orig`` and replaced by
    the preprocessed version. The preprocessors listed will be applied in
    order::

        for proc in preprocessors:
            script = proc(script, ...)

    Each entry in the `preprocessors` list should be the name of a registered
    preprocessor, see `troika.preprocess.preprocess`.
    """

    #: List of preprocessors to apply
    preprocessors = []

    def preprocess(self, script, user, output):
        """See `troika.sites.Site.preprocess`"""
        global preprocess
        preprocess.instantiate(self.preprocessors)
        script = pathlib.Path(script)
        orig_script = script.with_suffix(script.suffix + ".orig")
        if orig_script.exists():
            _logger.warning("Backup script file %r already exists, " +
                "overwriting", str(orig_script))
        with script.open(mode="r") as sin, \
                tempfile.NamedTemporaryFile(mode='w+', delete=False,
                    dir=script.parent, prefix=script.name) as sout:
            sin_pp = preprocess(sin, script, user, output)
            sout.writelines(sin_pp)
            new_script = pathlib.Path(sout.name)
        shutil.copymode(script, new_script)
        shutil.copy2(script, orig_script)
        new_script.replace(script)
        _logger.debug("Preprocessing done. Original script saved to %r",
            str(orig_script))
        return script


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
