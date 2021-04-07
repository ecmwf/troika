"""Slurm-managed site"""

import logging
import os
import pathlib
import re
import shutil
import tempfile

from .. import RunError
from ..utils import check_status
from .ssh import SSHSite

_logger = logging.getLogger(__name__)


def _split_slurm_directive(arg):
    """Split the argument of a Slurm directive

    >>> _split_slurm_directive("--output=foo")
    ('--output', 'foo')
    >>> _split_slurm_directive("-J job")
    ('-J', 'job')
    >>> _split_slurm_directive("--exclusive")
    ('--exclusive', None)
    """
    m = re.match(r"([^\s=]+)(=|\s+)?(.*)?$", arg)
    if m is None:
        raise RunError(r"Malformed sbatch argument: {arg!r}")
    key, sep, val = m.groups()
    if sep is None:
        assert val == ""
        val = None
    return key, val


_DIRECTIVE_RE = re.compile(r"^#\s*SBATCH\s+(.+)$")


def _pp_blanks(script, user, output, sin):
    """Remove blank lines at the top"""
    first = True
    for line in sin:
        if first:
            if line.isspace():
                continue
            first = False
        yield line


def _pp_output(script, user, output, sin):
    """Set the output file"""
    for line in sin:
        m = _DIRECTIVE_RE.match(line)
        if m is None:
            yield line
            continue
        key, val = _split_slurm_directive(m.group(1))
        if key in ["-o", "--output", "-e", "--error"]:
            continue
        yield line
    yield f"#SBATCH --output={output!s}\n"


def _pp_bubble(script, user, output, sin):
    """Make sure all Slurm directives are at the top"""
    with tempfile.SpooledTemporaryFile(max_size=1024**3, mode='w+',
            dir=script.parent, prefix=script.name) as tmp:
        first = True
        for line in sin:
            if first:
                first = False
                if line.startswith("#!"):
                    yield line
                    continue
            m = _DIRECTIVE_RE.match(line)
            if m is None:
                tmp.write(line)
                continue
            yield line
        tmp.seek(0)
        yield from tmp


class SlurmSite(SSHSite):
    """Site managed using Slurm"""

    SUBMIT_RE = re.compile(r"^Submitted batch job (\d+)$", re.MULTILINE)

    def __init__(self, config):
        super().__init__(config)
        self._sbatch = config.get('sbatch_command', 'sbatch')
        self._shell = [self._sbatch]

    def _parse_submit_output(self, out):
        match = self.SUBMIT_RE.search(out)
        if match is None:
            _logger.warn("Could not parse SLURM output %r", out)
            return None
        return int(match.group(1))

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
            for proc in [_pp_blanks, _pp_output, _pp_bubble]:
                sin_pp = proc(script, user, output, sin_pp)
            sout.writelines(sin_pp)
            new_script = pathlib.Path(sout.name)
        shutil.copymode(script, new_script)
        shutil.copy2(script, orig_script)
        new_script.replace(script)
        _logger.debug("Preprocessing done. Original script saved to %r",
            str(orig_script))
        return script

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script)
        sub_output = script.with_suffix(script.suffix + ".sub")
        if sub_output.exists():
            _logger.warning("Submission output file %r already exists, " +
                "overwriting", str(output))

        pid = super().submit(script, user, sub_output, dryrun=dryrun)
        if dryrun:
            return

        _, sts = os.waitpid(pid, 0)
        retcode = check_status(sts)
        if retcode != 0:
            msg = "Submission "
            if retcode > 0:
                msg += f"failed with exit code {retcode}"
            else:
                msg += f"terminated by signal {-retcode}"
            msg += f", check {str(sub_output)!r}"
            raise RunError(msg)

        jobid = self._parse_submit_output(sub_output.read_text())
        _logger.debug("Slurm job ID: %d", jobid)
        return jobid

    def __repr__(self):
        return f"{self.__class__.__name__}(host={self._host!r}, sbatch_command={self._sbatch!r})"
