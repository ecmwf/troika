"""Direct execution site"""

import logging
import os
import pathlib
import signal

from .. import InvocationError, RunError
from .base import Site

_logger = logging.getLogger(__name__)


class DirectExecSite(Site):
    """Site where jobs are run directly"""

    __type_name__ = "direct"

    def __init__(self, config, connection):
        super().__init__(config, connection)
        self._shell = config.get('shell', ['bash', '-s'])
        self._use_shell = config.get('use_shell', not connection.is_local())

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.Site.submit`"""
        script = pathlib.Path(script).resolve()
        if not script.exists():
            raise InvocationError(f"Script file {str(script)!r} does not exist")
        args = self._shell if self._use_shell else [script]
        output = pathlib.Path(output)
        if output.exists():
            _logger.warning("Output file %r already exists, overwriting",
                str(output))
        inpf = None
        if self._use_shell:
            inpf = script.open(mode="rb")
        outf = None
        if not dryrun:
            outf = output.open(mode="wb")
        proc = self._connection.execute(args, stdin=inpf, stdout=outf, detach=True,
            dryrun=dryrun)

        if dryrun:
            return

        jid_output = script.with_suffix(script.suffix + ".jid")
        if jid_output.exists():
            _logger.warning("Job ID output file %r already exists, " +
                "overwriting", str(jid_output))
        jid_output.write_text(str(proc.pid) + "\n")

        return proc

    def kill(self, script, user, jid=None, dryrun=False):
        """See `troika.sites.Site.kill`"""
        script = pathlib.Path(script)

        if jid is None:
            jid_output = script.with_suffix(script.suffix + ".jid")
            try:
                jid = jid_output.read_text().strip()
            except IOError as e:
                raise RunError(f"Could not read the job id: {e!s}")
        try:
            jid = int(jid)
        except ValueError:
            raise RunError(f"Invalid job id: {jid!r}")

        if dryrun:
            _logger.info(f"Sending SIGTERM to process {jid}")
            return

        _logger.debug(f"Sending SIGTERM to process {jid}")
        try:
            os.kill(jid, signal.SIGTERM)
        except ProcessLookupError:
            raise RunError(f"Process ID {jid} not found")

    def __repr__(self):
        return f"{self.__class__.__name__}(connection={self._connection!r}, use_shell={self._use_shell}, shell={self._shell!r})"
