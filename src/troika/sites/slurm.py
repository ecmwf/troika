"""Slurm-managed site"""

from collections import OrderedDict
import logging
import pathlib
import re
import signal
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
        "export_vars": b"--export=%s",
        "join_output_error": None,
        "licenses": b"--licenses=%s",
        "mail_type": b"--mail-type=%s",  # TODO: add translation logic
        "mail_user": b"--mail-user=%s",
        "memory_per_node": b"--mem=%s",
        "memory_per_cpu": b"--mem-per-cpu=%s",
        "name": b"--job-name=%s",
        "output_file": b"--output=%s",
        "partition": b"--partition=%s",
        "priority": b"--priority=%s",
        "tasks_per_node": b"--ntasks-per-node=%s",
        "threads_per_core": b"--threads-per-core=%s",
        "tmpdir_size": b"--tmp=%s",
        "total_nodes": b"--nodes=%s",
        "total_tasks": b"--ntasks=%s",
        "queue": b"--qos=%s",
        "walltime": b"--time=%s",
        "working_dir": b"--chdir=%s",
    }


    SUBMIT_RE = re.compile(br"^(?:Submitted batch job )?(\d+)$", re.MULTILINE)

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

    def _get_state(self, jid, strict=True):
        """Return the state of a SLURM job, or None if 'strict' is not in
        effect and it can't be retrieved (which probably means the job no
        longer exists)"""
        cmd = [ self._squeue, "-h", "-o", "%T", "-j", str(jid) ]
        proc = self._connection.execute(cmd, stdout=PIPE, stderr=PIPE)
        proc_stdout, proc_stderr = proc.communicate()
        retcode = proc.returncode
        # Essential to remove trailing newline from stdout before returning
        proc_stdout = proc_stdout.strip()
        proc_stderr = proc_stderr.strip()
        _logger.debug("squeue output for job %d: %s", jid, proc_stdout)
        if retcode != 0:
            _logger.error("squeue error: %s", proc_stderr)
            if strict:
                check_retcode(retcode, what="Get State")
        else:
            if proc_stderr:
                _logger.debug("squeue error output: %s", jid, proc_stderr)
        if proc_stdout: return proc_stdout.decode("ascii")

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script)

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

        proc = self._connection.execute(cmd, stdin=inpf, stdout=PIPE, stderr=PIPE, dryrun=dryrun)
        if dryrun:
            return

        proc_stdout, proc_stderr = proc.communicate()
        if proc.returncode != 0:
            if proc_stdout: _logger.error("sbatch stdout for script %s:\n%s", script, proc_stdout.strip())
            if proc_stderr: _logger.error("sbatch stderr for script %s:\n%s", script, proc_stderr.strip())
            check_retcode(proc.returncode, what="submission")
        else:
            if proc_stdout: _logger.debug("sbatch stdout for script %s:\n%s", script, proc_stdout.strip())
            if proc_stderr: _logger.debug("sbatch stderr for script %s:\n%s", script, proc_stderr.strip())

        jobid = self._parse_submit_output(proc_stdout)
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

        if user is None:
            user = "$USER"

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

        # Attempting to send a signal to a PENDING job will wait for it
        # to run first, which is not what we want. Cancel such jobs
        # directly, regardless of `_kill_sequence`. The "-t PENDING"
        # is important to prevent a race condition if the job is just
        # about to run.
        state = self._get_state(jid)
        if state == 'PENDING':
            cmd = [self._scancel, "-t", "PENDING", str(jid)]
            proc = self._connection.execute(cmd, stdout=PIPE, dryrun=dryrun)
            if not dryrun:
                proc_stdout, _ = proc.communicate()
                # Strip this _before_ checking for output because ecscancel
                # produces spurious blank lines
                proc_stdout = proc_stdout.strip()
                retcode = proc.returncode
                if retcode != 0:
                    _logger.error("scancel output: %s", proc_stdout)
                    check_retcode(retcode, what="Kill")
                elif proc_stdout:
                    _logger.debug("scancel output: %s", proc_stdout)

            state = self._get_state(jid, strict=False)
            if state is None or state == 'CANCELLED':
                return (jid, 'CANCELLED')
            elif state == 'PENDING':
                raise RunError(f"Failed to cancel PENDING job {jid!r}")
            # If anything else, the job is probably starting, so fall through
            # and treat like a running job

        seq = self._kill_sequence
        if seq is None:
            seq = [(0, None)]

        cancel_status = None
        for wait, sig in seq:
            time.sleep(wait)

            cmd = [self._scancel, str(jid)]
            if sig is not None:
                cmd.extend(["-f", "-s", str(sig.value)])
            proc = self._connection.execute(cmd, stdout=PIPE, dryrun=dryrun)

            if dryrun:
                continue

            proc_stdout, _ = proc.communicate()
            retcode = proc.returncode
            # Strip this _before_ checking for output because ecscancel
            # produces spurious blank lines
            proc_stdout = proc_stdout.strip()
            if retcode != 0:
                if cancel_status is None:
                    _logger.error("scancel output: %s", proc_stdout)
                    check_retcode(retcode, what="Kill")
                else:
                    if proc_stdout:
                        _logger.debug("scancel output: %s", proc_stdout)
                    break
            elif proc_stdout:
                _logger.debug("scancel output: %s", proc_stdout)

            if sig is None or sig == signal.SIGKILL:
                cancel_status = 'KILLED'
            elif cancel_status is None:
                cancel_status = 'TERMINATED'
        return (jid, cancel_status)

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
