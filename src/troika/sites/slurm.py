"""Slurm-managed site"""

import logging
import os
import pathlib
import re
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
    ('-j', 'job')
    >>> _split_slurm_directive("--exclusive")
    ('--exclusive', None)
    """
    m = re.match(r"([^\s=]+)(=|\s+)?(.*)?$", arg)
    if m is None:
        raise RunError(r"Malformed sbatch argument: {arg!r}")
    key, sep, val = m.groups()
    if sep == "":
        assert val == ""
        val = None
    return key, val


class SlurmSite(SSHSite):
    """Site managed using Slurm"""

    DIRECTIVE_RE = re.compile(r"^#\s*SBATCH\s+(.+)$")
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
        pp_script = script.with_suffix(script.suffix + ".pp")
        if pp_script.exists():
            _logger.warning("Preprocessed script file %r already exists, " +
                "overwriting", str(pp_script))
        with script.open(mode="r") as sin, \
                pp_script.open(mode='w') as sout, \
                tempfile.SpooledTemporaryFile(max_size=1024**3, mode='w+',
                    dir=pp_script.parent, prefix=pp_script.name) as tmp:
            first = True
            for line in sin:
                if first and line.isspace():
                    continue
                if first and line.startswith("#!"):
                    first = False
                    sout.write(line)
                    continue
                first = False
                m = self.DIRECTIVE_RE.match(line)
                if m is None:
                    tmp.write(line)
                    continue
                key, val = _split_slurm_directive(m.group(1))
                if key in ["-o", "--output", "-e", "--error"]:
                    continue
                sout.write(line)
            sout.write(f"#SBATCH --output={output!s}\n")
            tmp.seek(0)
            for line in tmp:
                sout.write(line)
        _logger.debug("Preprocessed output written to %r", str(pp_script))
        return pp_script

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
