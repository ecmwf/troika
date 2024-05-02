"""PBS-managed site"""

import locale
import logging
import pathlib
import re
import signal
import time
from collections import OrderedDict

from .. import InvocationError, RunError
from ..connection import PIPE
from ..parser import BaseParser
from ..utils import check_retcode, command_as_list
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


class PBSDirectiveParser(BaseParser):
    """Parser that processes a script to extract PBS directives

    Parameters
    ----------
    drop_keys: Iterable[bytes]
        Directives to ignore, e.g. ``[b'-o', b'-e']``

    Members
    -------
    data: collections.OrderedDict[bytes, (bytes or None, bytes)]
        Directives that have been parsed. The first item of the dict value is
        the parsed value, if any, and the second is the full line, including
        the line terminator.
    """

    DIRECTIVE_RE = re.compile(rb"^#\s*PBS\s+(.+)$")

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

        key, value = _split_pbs_directive(m.group(1))
        if key not in self.drop_keys:
            self.data[key] = (value, line)

        return True


def _translate_export_vars(value):
    if value == b"all":
        return b"-V"
    if value == b"none":
        return
    return b"-v %s" % value


def _translate_mail_type(value):
    trans = {b"none": b"n", b"begin": b"b", b"end": b"e", b"fail": b"a"}
    vals = value.split(b",")
    newvals = []
    for val in vals:
        newval = trans.get(val.lower())
        if newval is None:
            _logger.warn("Unknown mail_type value %r", val)
            newval = val
        newvals.append(newval)
    return b"-m %s" % b"".join(newvals)


class PBSSite(Site):
    """Site managed using PBS"""

    directive_prefix = b"#PBS "
    directive_translate = {
        "billing_account": b"-A %s",
        "error_file": b"-e %s",
        "export_vars": _translate_export_vars,
        "join_output_error": b"-j oe",  # TODO: make that automatic
        "mail_type": _translate_mail_type,
        "mail_user": b"-M %s",
        "name": b"-N %s",
        "output_file": b"-o %s",
        "priority": b"-p %s",
        "queue": b"-q %s",
        "walltime": b"-l walltime=%s",
    }

    def __init__(self, config, connection, global_config):
        super().__init__(config, connection, global_config)
        self._qsub = command_as_list(config.get("qsub_command", "qsub"))
        self._qdel = command_as_list(config.get("qdel_command", "qdel"))
        self._qsig = command_as_list(config.get("qsig_command", "qsig"))
        self._qstat = command_as_list(config.get("qstat_command", "qstat"))
        self._copy_script = config.get("copy_script", False)
        self._copy_jid = config.get("copy_jid", False)

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script)

        cmd = self._qsub.copy()

        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        inpf = None
        if self._copy_script:
            script_remote = pathlib.PurePath(output).parent / script.name
            self._connection.sendfile(script, script_remote, dryrun=dryrun)
            cmd.append(script_remote)
        else:
            inpf = script.open(mode="rb")

        proc = self._connection.execute(
            cmd, stdin=inpf, stdout=PIPE, stderr=PIPE, dryrun=dryrun
        )
        if dryrun:
            return

        proc_stdout, proc_stderr = proc.communicate()
        if proc.returncode != 0:
            if proc_stdout:
                _logger.error(
                    "qsub stdout for script %s:\n%s", script, proc_stdout.strip()
                )
            if proc_stderr:
                _logger.error(
                    "qsub stderr for script %s:\n%s", script, proc_stderr.strip()
                )
            check_retcode(proc.returncode, what="Submission")
        else:
            if proc_stdout:
                _logger.debug(
                    "qsub stdout for script %s:\n%s", script, proc_stdout.strip()
                )
            if proc_stderr:
                _logger.debug(
                    "qsub stderr for script %s:\n%s", script, proc_stderr.strip()
                )

        jobid = proc_stdout.decode(locale.getpreferredencoding()).strip()
        _logger.debug("PBS job ID: %s", jobid)

        jid_output = script.with_suffix(script.suffix + ".jid")
        if jid_output.exists():
            _logger.warning(
                "Job ID output file %r already exists, " + "overwriting",
                str(jid_output),
            )
        jid_output.write_text(str(jobid) + "\n")

        if self._copy_jid:
            jid_remote = pathlib.PurePath(output).parent / jid_output.name
            _logger.debug("Copying JID to output directory: %s", jid_remote)
            self._connection.sendfile(jid_output, jid_remote, dryrun=dryrun)

        return jobid

    def monitor(self, script, user, output=None, jid=None, dryrun=False):
        """See `troika.sites.Site.monitor`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script, output)
            _logger.debug(f"Read job id {jid!r} from jidfile")
        else:
            _logger.debug(f"Using specified job id {jid!r}")

        stat_output = script.with_suffix(script.suffix + ".stat")
        if stat_output.exists():
            _logger.warning(
                "Status file %r already exists, overwriting", str(stat_output)
            )
        outf = None
        if not dryrun:
            outf = stat_output.open(mode="wb")

        self._connection.execute(self._qstat + [jid], stdout=outf, dryrun=dryrun)

        _logger.info("Output written to %r", str(stat_output))

    def kill(self, script, user, output=None, jid=None, dryrun=False):
        """See `troika.sites.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script, output)
            _logger.debug(f"Read job id {jid!r} from jidfile")
        else:
            _logger.debug(f"Using specified job id {jid!r}")

        seq = self._kill_sequence
        if not seq:
            seq = [(0, None)]

        cancel_status = None
        for wait, sig in seq:
            time.sleep(wait)

            cmd = self._qdel + [jid]
            if sig is not None:
                cmd = self._qsig + ["-s", str(sig.value), jid]
            proc = self._connection.execute(cmd, stdout=PIPE, dryrun=dryrun)

            if dryrun:
                continue

            proc_stdout, _ = proc.communicate()
            retcode = proc.returncode
            if retcode != 0:
                if cancel_status is None:
                    _logger.error("qdel/qsig output: %s", proc_stdout)
                    check_retcode(retcode, what="Kill")
                else:
                    _logger.debug("qdel/qsig output: %s", proc_stdout)
                    break

            if sig is None or sig == signal.SIGKILL:
                cancel_status = "KILLED"
            elif cancel_status is None:
                cancel_status = "TERMINATED"

        return (jid, cancel_status)

    def get_native_parser(self):
        """See `troika.sites.Site.get_native_parser`"""
        return PBSDirectiveParser(drop_keys=[b"-o", b"-e", b"-j"])

    def _parse_jidfile(self, script, output=None, dryrun=False):
        script = pathlib.Path(script)
        jid_output = script.with_suffix(script.suffix + ".jid")
        try:
            return jid_output.read_text().strip()
        except IOError as e:
            if self._copy_jid and output is not None:
                jid_remote = pathlib.PurePath(output).parent / jid_output.name
                try:
                    self._connection.getfile(jid_remote, jid_output, dryrun=dryrun)
                    _logger.debug(
                        "Job ID file copied back from output directory: %s", jid_remote
                    )
                    if not dryrun:
                        return jid_output.read_text().strip()
                except (IOError, RunError) as e2:
                    raise RunError(
                        f"Could not read the job id: {e!s} or copy it back {e2!s}"
                    )
            raise RunError(f"Could not read the job id: {e!s}")

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, qsub_command={self._qsub[0]!r})"
