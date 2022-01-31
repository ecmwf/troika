"""Slurm-managed site"""

from collections import OrderedDict
import logging
import pathlib
import re
import time

from .. import InvocationError, RunError
from ..connection import PIPE
from ..parser import BaseParser, ParseError
from ..utils import check_retcode
from .base import Site

_logger = logging.getLogger(__name__)


def _split_slurm_directive(arg):
    """Split the argument of a Slurm directive

    >>> _split_slurm_directive(b"--output=foo")
    (b'--output', b'foo')
    >>> _split_slurm_directive(b"-J job")
    (b'-J', b'job')
    >>> _split_slurm_directive(b"--exclusive")
    (b'--exclusive', None)
    """
    m = re.match(rb"([^\s=]+)(=|\s+)?(.*)?$", arg)
    if m is None:
        raise ParseError(r"Malformed sbatch argument: {arg!r}")
    key, sep, val = m.groups()
    if sep is None:
        assert val == b""
        val = None
    return key, val


class SlurmDirectiveParser(BaseParser):
    """Parser that processes a script to extract Slurm directives

    Parameters
    ----------
    drop_keys: Iterable[bytes]
        Directives to ignore, e.g. ``[b'-o', b'--output']``

    Members
    -------
    data: collections.OrderedDict[bytes, (bytes or None, bytes)]
        Directives that have been parsed. The first item of the dict value is
        the parsed value, if any, and the second is the full line, including
        the line terminator.
    """

    DIRECTIVE_RE = re.compile(rb"^#\s*SBATCH\s+(.+)$")

    def __init__(self, drop_keys=None):
        super().__init__()
        self.data = OrderedDict()
        if drop_keys is None:
            drop_keys = []
        self.drop_keys = set(drop_keys)

    def feed(self, line):
        """Process the given line

        See ``BaseParser.feed``
        """
        m = self.DIRECTIVE_RE.match(line)
        if m is None:
            return False

        key, value = _split_slurm_directive(m.group(1))
        if key not in self.drop_keys:
            self.data[key] = (value, line)

        return True


class SlurmSite(Site):
    """Site managed using Slurm"""


    directive_prefix = b"#SBATCH "
    directive_translate = {
        "billing_account": b"--account=%s",
        "cpus_per_task": b"--cpus-per-task=%s",
        "error_file": b"--error=%s",
        "exclusive_resources": b"--exclusive",
        "export_vars": b"--export=%s",
        "mail_type": b"--mail-type=%s",  # TODO: add translation logic
        "mail_user": b"--mail-user=%s",
        "memory_per_node": b"--mem=%s",
        "memory_per_cpu": b"--mem-per-cpu=%s",
        "name": b"--job-name=%s",
        "output_file": b"--output=%s",
        "partition": b"--partition=%s",
        "tasks_per_node": b"--ntasks-per-node=%s",
        "threads_per_core": b"--threads-per-core=%s",
        "tmpdir_size": b"--tmp=%s",
        "total_nodes": b"--nodes=%s",
        "total_tasks": b"--ntasks=%s",
        "queue": b"--qos=%s",
        "walltime": b"--time=%s",
    }


    SUBMIT_RE = re.compile(r"^Submitted batch job (\d+)$", re.MULTILINE)

    def __init__(self, config, connection, global_config):
        super().__init__(config, connection, global_config)
        self._sbatch = config.get('sbatch_command', 'sbatch')
        self._scancel = config.get('scancel_command', 'scancel')
        self._squeue = config.get('squeue_command', 'squeue')
        self._copy_script = config.get('copy_script', False)

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

        cmd = [self._sbatch]

        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        inpf = None
        if self._copy_script:
            script_remote = pathlib.PurePath(output).parent / script.name
            self._connection.sendfile(script, script_remote, dryrun=dryrun)
            cmd.append(script_remote)
        else:
            inpf = script.open(mode="rb")

        outf = None
        if not dryrun:
            outf = sub_output.open(mode="wb")

        proc = self._connection.execute(cmd, stdin=inpf, stdout=outf,
            dryrun=dryrun)
        if dryrun:
            return

        retcode = proc.wait()
        check_retcode(retcode, what="Submission",
            suffix=f", check {str(sub_output)!r}")

        jobid = self._parse_submit_output(sub_output.read_text())
        _logger.debug("Slurm job ID: %d", jobid)

        jid_output = script.with_suffix(script.suffix + ".jid")
        if jid_output.exists():
            _logger.warning("Job ID output file %r already exists, " +
                "overwriting", str(jid_output))
        jid_output.write_text(str(jobid) + "\n")

        return jobid

    def monitor(self, script, user, jid=None, dryrun=False):
        """See `troika.sites.Site.monitor`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script)
        try:
            jid = int(jid)
        except ValueError:
            raise RunError(f"Invalid job id: {jid!r}")

        stat_output = script.with_suffix(script.suffix + ".stat")
        if stat_output.exists():
            _logger.warning("Status file %r already exists, overwriting",
                str(stat_output))
        outf = None
        if not dryrun:
            outf = stat_output.open(mode="wb")

        self._connection.execute([self._squeue, "-u", user, "-j", str(jid)],
            stdout=outf, dryrun=dryrun)

        _logger.info("Output written to %r", str(stat_output))

    def kill(self, script, user, jid=None, dryrun=False):
        """See `troika.sites.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script)
        try:
            jid = int(jid)
        except ValueError:
            raise RunError(f"Invalid job id: {jid!r}")

        seq = self._kill_sequence
        if seq is None:
            seq = [(0, None)]

        first = True
        for wait, sig in seq:
            time.sleep(wait)

            cmd = [self._scancel, str(jid)]
            if sig is not None:
                cmd.extend(["-s", str(int(sig))])
            proc = self._connection.execute(cmd, stdout=PIPE, dryrun=dryrun)

            if dryrun:
                continue

            proc_stdout, _ = proc.communicate()
            retcode = proc.returncode
            if retcode != 0:
                if first:
                    _logger.error("scancel output: %s", proc_stdout)
                    check_retcode(retcode, what="Kill")
                else:
                    return

            first = False

    def get_native_parser(self):
        """See `troika.sites.Site.get_native_parser`"""
        return SlurmDirectiveParser(drop_keys=[b'-o', b'--output', b'-e', b'--error'])

    def _parse_jidfile(self, script):
        script = pathlib.Path(script)
        jid_output = script.with_suffix(script.suffix + ".jid")
        try:
            return jid_output.read_text().strip()
        except IOError as e:
            raise RunError(f"Could not read the job id: {e!s}")

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, sbatch_command={self._sbatch!r})"
