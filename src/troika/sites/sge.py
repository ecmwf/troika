"""SGE-managed site"""

from __future__ import annotations

import locale
import logging
import pathlib
import re
from collections import OrderedDict
from subprocess import PIPE
from typing import IO, TYPE_CHECKING, Any

from .. import InvocationError, RunError
from ..parser import BaseParser
from ..utils import check_retcode, command_as_list
from .base import Site

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from ..config import Config
    from ..connections.base import Connection
    from .base import StrPath

_logger = logging.getLogger(__name__)


def _split_sge_directive(arg: bytes) -> tuple[bytes, bytes | None]:
    """Split the argument of a SGE directive

    >>> _split_sge_directive(b"-o foo")
    (b'-o', b'foo')
    >>> _split_sge_directive(b"-N job")
    (b'-N', b'job')
    >>> _split_sge_directive(b"-V")
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


class SGEDirectiveParser(BaseParser):
    """Parser that processes a script to extract SGE directives

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

    DIRECTIVE_RE = re.compile(rb"^#\s*\$\s+(.+)$")

    def __init__(self, drop_keys: Iterable[bytes] | None = None) -> None:
        super().__init__()
        self.data: OrderedDict[bytes, tuple[bytes | None, bytes]] = OrderedDict()
        if drop_keys is None:
            drop_keys = []
        self.drop_keys = set(drop_keys)

    def feed(self, line: bytes) -> bool:
        """Process the given line

        See ``BaseParser.feed``
        """
        m = self.DIRECTIVE_RE.match(line)
        if m is None:
            return False

        key, value = _split_sge_directive(m.group(1))
        if key not in self.drop_keys:
            self.data[key] = (value, line)

        return True


def _translate_export_vars(value: Any) -> bytes | None:
    if value == b"all":
        return b"-V"
    if value == b"none":
        return None
    return b"-v %s" % value


def _translate_mail_type(value: bytes) -> bytes:
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


class SGESite(Site):
    """Site managed using SGE"""

    directive_prefix = b"#$ "
    directive_translate = {
        "billing_account": b"-A %s",
        "error_file": b"-e %s",
        "export_vars": _translate_export_vars,
        "mail_type": _translate_mail_type,
        "join_output_error": b"-j y",  # TODO: make that automatic
        "mail_user": b"-M %s",
        "name": b"-N %s",
        "output_file": b"-o %s",
        "priority": b"-p %s",
        "queue": b"-q %s",
        "walltime": b"-l h_rt=%s",
    }

    SUBMIT_RE = re.compile(r"(Your job )?(\d+)")

    def __init__(self, config: Mapping[str, Any], connection: Connection, global_config: Config) -> None:
        super().__init__(config, connection, global_config)
        self._qsub = command_as_list(config.get("qsub_command", "qsub"))
        self._qdel = command_as_list(config.get("qdel_command", "qdel"))
        self._qstat = command_as_list(config.get("qstat_command", "qstat"))
        self._copy_script = config.get("copy_script", False)
        self._copy_jid = config.get("copy_jid", False)

    def _parse_submit_output(self, out: str) -> int | None:
        match = self.SUBMIT_RE.search(out)
        if match is None:
            _logger.warn("Could not parse SGE output %r", out)
            return None
        return int(match.group(2))

    def submit(self, script: StrPath, user: str | None, output: StrPath, dryrun: bool = False) -> int | None:
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script)

        cmd = self._qsub.copy()

        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        inpf: IO[bytes] | None = None
        if self._copy_script:
            script_remote = pathlib.PurePath(output).parent / script.name
            self._connection.sendfile(script, script_remote, dryrun=dryrun)
            cmd.append(script_remote)
        else:
            inpf = script.open(mode="rb")

        proc = self._connection.execute(cmd, stdin=inpf, stdout=PIPE, stderr=PIPE, dryrun=dryrun)
        if dryrun:
            return None

        assert proc is not None  # execute only returns None when dryrun is True
        proc_stdout, proc_stderr = proc.communicate()
        if proc.returncode != 0:
            if proc_stdout:
                _logger.error("qsub stdout for script %s:\n%s", script, proc_stdout.strip())
            if proc_stderr:
                _logger.error("qsub stderr for script %s:\n%s", script, proc_stderr.strip())
            check_retcode(proc.returncode, what="Submission")
        else:
            if proc_stdout:
                _logger.debug("qsub stdout for script %s:\n%s", script, proc_stdout.strip())
            if proc_stderr:
                _logger.debug("qsub stderr for script %s:\n%s", script, proc_stderr.strip())

        jobid = self._parse_submit_output(proc_stdout.decode(locale.getpreferredencoding()).strip())
        _logger.debug("SGE job ID: %s", jobid)

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

    def monitor(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> None:
        """See `troika.sites.Site.monitor`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script, output)
            _logger.debug(f"Read job id {jid!r} from jidfile")
        else:
            _logger.debug(f"Using specified job id {jid!r}")

        stat_output = script.with_suffix(script.suffix + ".stat")
        if stat_output.exists():
            _logger.warning("Status file %r already exists, overwriting", str(stat_output))
        outf: IO[bytes] | None = None
        if not dryrun:
            outf = stat_output.open(mode="wb")

        self._connection.execute(self._qstat + ["-j", jid], stdout=outf, dryrun=dryrun)

        _logger.info("Output written to %r", str(stat_output))

    def kill(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> tuple[str, str]:
        """See `troika.sites.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script, output)
            _logger.debug(f"Read job id {jid!r} from jidfile")
        else:
            _logger.debug(f"Using specified job id {jid!r}")

        cmd = self._qdel + [jid]
        proc = self._connection.execute(cmd, stdout=PIPE, dryrun=dryrun)

        if dryrun:
            return (jid, "KILLED")

        assert proc is not None  # execute only returns None when dryrun is True
        proc_stdout, _ = proc.communicate()
        retcode = proc.returncode
        if retcode != 0:
            _logger.error("qdel output: %s", proc_stdout)
            check_retcode(retcode, what="Kill")

        return (jid, "KILLED")

    def get_native_parser(self) -> BaseParser:
        """See `troika.sites.Site.get_native_parser`"""
        return SGEDirectiveParser(drop_keys=[b"-o", b"-e", b"-j"])

    def _parse_jidfile(self, script: StrPath, output: StrPath | None = None, dryrun: bool = False) -> str:
        script = pathlib.Path(script)
        jid_output = script.with_suffix(script.suffix + ".jid")
        try:
            return jid_output.read_text().strip()
        except OSError as e:
            if self._copy_jid and output is not None:
                jid_remote = pathlib.PurePath(output).parent / jid_output.name
                try:
                    self._connection.getfile(jid_remote, jid_output, dryrun=dryrun)
                    _logger.debug("Job ID file copied back from output directory: %s", jid_remote)
                    if not dryrun:
                        return jid_output.read_text().strip()
                except (OSError, RunError) as e2:
                    raise RunError(f"Could not read the job id: {e!s} or copy it back {e2!s}")
            raise RunError(f"Could not read the job id: {e!s}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(connection={self._connection!r}, qsub_command={self._qsub[0]!r})"
