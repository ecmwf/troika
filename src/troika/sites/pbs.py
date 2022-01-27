"""PBS-managed site"""

import logging
import os
import pathlib
import re
import tempfile
import time

from .. import InvocationError, RunError
from ..connection import PIPE
from ..preprocess import preprocess
from ..utils import check_retcode
from .base import Site

_logger = logging.getLogger(__name__)


def _split_pbs_directive(arg):
    """Split the argument of a PBS directive

    >>> _split_pbs_directive(b"-o foo")
    (b'-o', b'foo')
    >>> _split_pbs_directive(b"-N job")
    (b'-N', b'job')
    >>> _split_pbs_directive(b"-V")
    (b'-V', None)
    """
    m = re.match(rb"(\S+)(\s+)?(.*)?$", arg)
    if m is None:
        raise RunError(r"Malformed qsub argument: {arg!r}")
    key, sep, val = m.groups()
    if sep is None:
        assert val == b""
        val = None
    return key, val


_DIRECTIVE_RE = re.compile(rb"^#\s*PBS\s+(.+)$")


@preprocess.register
def pbs_add_output(sin, script, user, output):
    """Set the output file"""
    for line in sin:
        m = _DIRECTIVE_RE.match(line)
        if m is None:
            yield line
            continue
        key, val = _split_pbs_directive(m.group(1))
        if key in [b"-o", b"-e", b"-j"]:
            continue
        yield line
    yield b"#PBS -j oe\n"
    yield b"#PBS -o " + os.fsencode(output) + b"\n"


@preprocess.register
def pbs_bubble(sin, script, user, output):
    """Make sure all PBS directives are at the top"""
    directives = []
    with tempfile.SpooledTemporaryFile(max_size=1024**3, mode='w+b',
            dir=script.parent, prefix=script.name) as tmp:
        first = True
        for line in sin:
            if line.isspace():
                tmp.write(line)
                continue

            m = _DIRECTIVE_RE.match(line)
            if m is not None:
                directives.append(line)
                continue

            if first:
                first = False
                if line.startswith(b"#!"):
                    yield line
                    continue

            tmp.write(line)

        yield from directives
        tmp.seek(0)
        yield from tmp


class PBSSite(Site):
    """Site managed using PBS"""


    def __init__(self, config, connection, global_config):
        super().__init__(config, connection, global_config)
        self._qsub = config.get('qsub_command', 'qsub')
        self._qdel = config.get('qdel_command', 'qdel')
        self._qsig = config.get('qsig_command', 'qsig')
        self._qstat = config.get('qstat_command', 'qstat')
        self._copy_script = config.get('copy_script', False)

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script)
        sub_output = script.with_suffix(script.suffix + ".sub")
        if sub_output.exists():
            _logger.warning("Submission output file %r already exists, " +
                "overwriting", str(sub_output))
        sub_error = script.with_suffix(script.suffix + ".suberr")
        if sub_error.exists():
            _logger.warning("Submission error file %r already exists, " +
                "overwriting", str(sub_error))

        cmd = [self._qsub]

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
        errf = None
        if not dryrun:
            outf = sub_output.open(mode="wb")
            errf = sub_error.open(mode="wb")

        proc = self._connection.execute(cmd, stdin=inpf, stdout=outf, stderr=errf,
            dryrun=dryrun)
        if dryrun:
            return

        retcode = proc.wait()
        check_retcode(retcode, what="Submission",
            suffix=f", check {str(sub_output)!r} and {str(sub_error)!r}")

        jobid = sub_output.read_text().strip()
        _logger.debug("PBS job ID: %s", jobid)

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

        stat_output = script.with_suffix(script.suffix + ".stat")
        if stat_output.exists():
            _logger.warning("Status file %r already exists, overwriting",
                str(stat_output))
        outf = None
        if not dryrun:
            outf = stat_output.open(mode="wb")

        self._connection.execute([self._qstat, jid], stdout=outf, dryrun=dryrun)

        _logger.info("Output written to %r", str(stat_output))

    def kill(self, script, user, jid=None, dryrun=False):
        """See `troika.sites.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script)

        seq = self._kill_sequence
        if seq is None:
            seq = [(0, None)]

        first = True
        for wait, sig in seq:
            time.sleep(wait)

            cmd = [self._qdel, jid]
            if sig is not None:
                cmd = [self._qsig, "-s", str(int(sig)), jid]
            proc = self._connection.execute(cmd, stdout=PIPE, dryrun=dryrun)

            if dryrun:
                continue

            proc_stdout, _ = proc.communicate()
            retcode = proc.returncode
            if retcode != 0:
                if first:
                    _logger.error("qdel/qsig output: %s", proc_stdout)
                    check_retcode(retcode, what="Kill")
                else:
                    return

            first = False

    def _parse_jidfile(self, script):
        script = pathlib.Path(script)
        jid_output = script.with_suffix(script.suffix + ".jid")
        try:
            return jid_output.read_text().strip()
        except IOError as e:
            raise RunError(f"Could not read the job id: {e!s}")

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, qsub_command={self._qsub!r})"
