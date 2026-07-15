"""Direct execution site"""

from __future__ import annotations

import logging
import os
import pathlib
import signal
import time
from typing import IO, TYPE_CHECKING, Any

from .. import ConfigurationError, InvocationError, RunError
from .base import BaseSite

if TYPE_CHECKING:
    from collections.abc import Mapping
    from subprocess import Popen

    from ..config import Config
    from ..connections.base import Connection
    from .base import StrPath

_logger = logging.getLogger(__name__)


class DirectExecSite(BaseSite):
    """Site where jobs are run directly"""

    __type_name__ = "direct"

    def __init__(self, config: Mapping[str, Any], connection: Connection, global_config: Config) -> None:
        super().__init__(config, connection, global_config)
        self._copy_script = config.get("copy_script", False)
        self._copy_jid = config.get("copy_jid", False)
        self._shell = config.get("shell", ["bash"] if self._copy_script else ["bash", "-s"])
        self._use_shell = config.get("use_shell", not connection.is_local())

        if not (connection.is_local() or self._copy_script or self._use_shell):
            raise ConfigurationError("copy_script and use_shell cannot both be False for a remote site")

    def submit(self, script: StrPath, user: str | None, output: StrPath, dryrun: bool = False) -> Popen[Any] | None:
        """See `troika.sites.base.Site.submit`"""
        script = pathlib.Path(script).resolve()
        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")

        script_remote: pathlib.PurePath = script
        if self._copy_script and not self._connection.is_local():
            script_remote = pathlib.PurePath(output).parent / script.name
            super().create_output_dir(script_remote, dryrun=dryrun)
            self._connection.sendfile(script, script_remote, dryrun=dryrun)

        args: list[str] = []
        if self._use_shell:
            args.extend(self._shell)
        if self._copy_script or (self._connection.is_local() and not self._use_shell):
            args.append(str(script_remote))

        inpf: IO[bytes] | None = None
        if self._use_shell and not self._copy_script:
            inpf = script.open(mode="rb")

        output = pathlib.Path(output)
        self.create_output_dir(output, dryrun=dryrun)
        if output.exists():
            _logger.warning("Output file %r already exists, overwriting", str(output))
        outf: IO[bytes] | None = None
        if not dryrun:
            outf = output.open(mode="wb")
        proc = self._connection.execute(args, stdin=inpf, stdout=outf, detach=True, dryrun=dryrun)

        if dryrun:
            return None

        assert proc is not None  # execute only returns None when dryrun is True
        jid_output = script.with_suffix(script.suffix + ".jid")
        if jid_output.exists():
            _logger.warning(
                "Job ID output file %r already exists, " + "overwriting",
                str(jid_output),
            )
        jid_output.write_text(str(proc.pid) + "\n")

        if self._copy_jid:
            jid_remote = pathlib.PurePath(output).parent / jid_output.name
            _logger.debug("Copying JID to output directory: %s", jid_remote)
            self._connection.sendfile(jid_output, jid_remote, dryrun=dryrun)

        return proc

    def monitor(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> None:
        """See `troika.sites.base.Site.monitor`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script, output)
            _logger.debug(f"Read job id {jid!r} from jidfile")
        else:
            _logger.debug(f"Using specified job id {jid!r}")
        try:
            jid_num = int(jid)
        except ValueError:
            raise RunError(f"Invalid job id: {jid!r}")

        stat_output = script.with_suffix(script.suffix + ".stat")
        if stat_output.exists():
            _logger.warning("Status file %r already exists, overwriting", str(stat_output))
        outf: IO[bytes] | None = None
        if not dryrun:
            outf = stat_output.open(mode="wb")

        conn = self._connection.get_parent()
        conn.execute(["ps", "-lyfp", str(jid_num)], stdout=outf, dryrun=dryrun)

        _logger.info("Output written to %r", str(stat_output))

    def kill(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> tuple[int, str | None]:
        """See `troika.sites.base.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid = self._parse_jidfile(script, output)
            _logger.debug(f"Read job id {jid!r} from jidfile")
        else:
            _logger.debug(f"Using specified job id {jid!r}")
        try:
            jid_num = int(jid)
        except ValueError:
            raise RunError(f"Invalid job id: {jid!r}")

        seq = self._kill_sequence
        if not seq:
            seq = [(0, signal.SIGTERM)]

        cancel_status: str | None = None
        for wait, sig in seq:
            time.sleep(wait)
            if sig is None:
                sig = signal.SIGTERM

            if dryrun:
                _logger.info(f"Sending {sig.name} to process {jid_num}")
                continue

            _logger.debug(f"Sending {sig.name} to process {jid_num}")
            try:
                os.kill(jid_num, sig.value)
            except ProcessLookupError:
                if cancel_status is None:
                    raise RunError(f"Process ID {jid_num} not found")
                else:
                    break

            if sig == signal.SIGKILL:
                cancel_status = "KILLED"
            else:
                cancel_status = "TERMINATED"

        return (jid_num, cancel_status)

    def create_output_dir(self, output: StrPath, dryrun: bool = False) -> pathlib.Path:
        """See `troika.sites.base.Site.create_output_dir`"""
        out_dir = pathlib.Path(output).parent
        if dryrun:
            _logger.info("Ensuring directory %r exists", str(out_dir))
        else:
            _logger.debug("Ensuring directory %r exists", str(out_dir))
            out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

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
        return (
            f"{self.__class__.__name__}("
            f"connection={self._connection!r}, "
            f"use_shell={self._use_shell}, "
            f"shell={self._shell!r})"
        )
