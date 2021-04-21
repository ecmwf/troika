"""Slurm-managed site"""

import logging
import os
import pathlib
import re
import tempfile

from .. import InvocationError, RunError
from ..connection import SSHConnection
from ..preprocess import PreprocessMixin, remove_top_blank_lines
from ..utils import check_status
from .base import Site

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


class SlurmSite(PreprocessMixin, Site):
    """Site managed using Slurm"""

    SUBMIT_RE = re.compile(r"^Submitted batch job (\d+)$", re.MULTILINE)

    preprocessors = [remove_top_blank_lines, _pp_output, _pp_bubble]

    def __init__(self, config, connection):
        super().__init__(config, connection)
        self._sbatch = config.get('sbatch_command', 'sbatch')

    def _parse_submit_output(self, out):
        match = self.SUBMIT_RE.search(out)
        if match is None:
            _logger.warn("Could not parse SLURM output %r", out)
            return None
        return int(match.group(1))

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script)
        sub_output = script.with_suffix(script.suffix + ".sub")
        if sub_output.exists():
            _logger.warning("Submission output file %r already exists, " +
                "overwriting", str(output))

        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        inpf = script.open(mode="rb")
        outf = None
        if not dryrun:
            outf = sub_output.open(mode="wb")
        pid = self._connection.execute([self._sbatch], stdin=inpf, stdout=outf,
            dryrun=dryrun)
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
        return f"{self.__class__.__name__}(connection={self._connection!r}, sbatch_command={self._sbatch!r})"
