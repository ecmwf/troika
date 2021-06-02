"""Slurm-managed site"""

import logging
import pathlib
import re
import tempfile

from .. import InvocationError, RunError
from ..connection import PIPE
from ..preprocess import preprocess
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


@preprocess.register
def slurm_add_output(sin, script, user, output):
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


@preprocess.register
def slurm_bubble(sin, script, user, output):
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


class SlurmSite(Site):
    """Site managed using Slurm"""

    SUBMIT_RE = re.compile(r"^Submitted batch job (\d+)$", re.MULTILINE)

    def __init__(self, config, connection):
        super().__init__(config, connection)
        self._sbatch = config.get('sbatch_command', 'sbatch')
        self._scancel = config.get('scancel_command', 'scancel')

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
                "overwriting", str(sub_output))

        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        inpf = script.open(mode="rb")
        outf = None
        if not dryrun:
            outf = sub_output.open(mode="wb")
        proc = self._connection.execute([self._sbatch], stdin=inpf, stdout=outf,
            dryrun=dryrun)
        if dryrun:
            return

        retcode = proc.wait()
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

        jid_output = script.with_suffix(script.suffix + ".jid")
        if jid_output.exists():
            _logger.warning("Job ID output file %r already exists, " +
                "overwriting", str(jid_output))
        jid_output.write_text(str(jobid) + "\n")

        return jobid

    def kill(self, script, user, jid=None, dryrun=False):
        """See `troika.sites.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid_output = script.with_suffix(script.suffix + ".jid")
            try:
                jid_s = jid_output.read_text().strip()
            except IOError as e:
                raise RunError(f"Could not read the job id: {e!s}")
            try:
                jid = int(jid_s)
            except ValueError:
                raise RunError(f"Invalid job id: {jid_s!r}")

        proc = self._connection.execute([self._scancel, str(jid)], stdout=PIPE,
            dryrun=dryrun)
        if dryrun:
            return

        proc_stdout, _ = proc.communicate()
        retcode = proc.returncode
        if retcode != 0:
            _logger.error("scancel output: %s", proc_stdout)
            msg = "Kill "
            if retcode > 0:
                msg += f"failed with exit code {retcode}"
            else:
                msg += f"terminated by signal {-retcode}"
            raise RunError(msg)

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, sbatch_command={self._sbatch!r})"
