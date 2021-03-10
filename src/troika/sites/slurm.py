"""Slurm-managed site"""

import logging
import os
import pathlib
import re

from .. import RunError
from ..utils import check_status
from .ssh import SSHSite

_logger = logging.getLogger(__name__)


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
