"""Script preprocessing utilities"""

import logging
import pathlib
import shutil
import tempfile

_logger = logging.getLogger(__name__)


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
            script = proc(..., script)

    Each preprocessor should iterate over the lines of the script, and have the
    following signature::

        def preprocessor(script_path: Path, user: str, output: Union[str, Path],
                         script_in: Iterable[str]) -> Iterable[str]
    """

    #: List of preprocessors to apply
    preprocessors = []

    def preprocess(self, script, user, output):
        """See `troika.sites.Site.preprocess`"""
        script = pathlib.Path(script)
        orig_script = script.with_suffix(script.suffix + ".orig")
        if orig_script.exists():
            _logger.warning("Backup script file %r already exists, " +
                "overwriting", str(orig_script))
        with script.open(mode="r") as sin, \
                tempfile.NamedTemporaryFile(mode='w+', delete=False,
                    dir=script.parent, prefix=script.name) as sout:
            sin_pp = sin
            for proc in self.preprocessors:
                sin_pp = proc(script, user, output, sin_pp)
            sout.writelines(sin_pp)
            new_script = pathlib.Path(sout.name)
        shutil.copymode(script, new_script)
        shutil.copy2(script, orig_script)
        new_script.replace(script)
        _logger.debug("Preprocessing done. Original script saved to %r",
            str(orig_script))
        return script


def remove_top_blank_lines(script, user, output, sin):
    """Remove blank lines at the top of the script"""
    first = True
    for line in sin:
        if first:
            if line.isspace():
                continue
            first = False
        yield line
