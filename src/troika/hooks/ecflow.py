"""ecFlow hooks"""

import logging
import pathlib

from .. import InvocationError, RunError
from ..connection import PIPE
from ..connections.local import LocalConnection
from ..parser import DirectiveParser
from ..utils import check_retcode

_logger = logging.getLogger(__name__)


def abort_on_ecflow(site, script, output, jid, cancel_status, dryrun=False):
    """Post-kill hook to issue an abort on behalf of a job that was killed
    or cancelled without the opportunity to inform ecFlow itself."""
    if cancel_status == "CANCELLED":
        msg = "Cancelled before starting"
    elif cancel_status == "KILLED":
        msg = "Killed forcefully"
    elif cancel_status == "VANISHED":
        msg = "Vanished unexpectedly"
    elif cancel_status == "TERMINATED":
        return
    else:
        raise InvocationError(
            f'abort_on_ecflow: unknown cancel status "{cancel_status}"'
        )

    script = pathlib.Path(script)
    orig_script = script.with_suffix(script.suffix + ".orig")

    if not orig_script.exists():
        orig_script_copy = pathlib.PurePath(output).parent / orig_script.name
        if output is not None:
            try:
                site._connection.getfile(orig_script_copy, orig_script, dryrun=dryrun)
                _logger.debug(
                    f"Original script copied back from output directory: {orig_script_copy!r}"
                )
            except (IOError, RunError) as e:
                raise RunError(f"Could not copy back original script {e!s}")

    parser = DirectiveParser()
    with open(orig_script, "rb") as sin:
        for line in sin:
            parser.feed(line)
    env = {}
    for directive, var, required in [
        ("ecflow_name", "ECF_NAME", True),
        ("ecflow_pass", "ECF_PASS", True),
        ("ecflow_host", "ECF_HOST", False),
        ("ecflow_port", "ECF_PORT", False),
    ]:
        try:
            env[var] = parser.data[directive].decode("ascii")
        except KeyError:
            if required:
                _logger.error(
                    f"abort_on_ecflow could not find {directive} defined in script {script}"
                )
                raise

    cmd = [parser.data.get("ecflow_client", "ecflow_client"), f"--abort={msg}"]

    if site._connection.is_local():
        _logger.debug(
            f'abort_on_ecflow running {" ".join(cmd)} on local site with env {env!r}'
        )
        connection = site._connection
    elif "ecflow_host" in env:
        _logger.debug(
            f'abort_on_ecflow running {" ".join(cmd)} on remote site with env {env!r}'
        )
        connection = site._connection
    else:
        _logger.debug(
            f'abort_on_ecflow running {" ".join(cmd)} locally with env {env!r}'
        )
        connection = LocalConnection({}, site._connection.user)

    proc = connection.execute(cmd, stdout=PIPE, stderr=PIPE, env=env, dryrun=dryrun)
    if dryrun:
        return

    proc_stdout, proc_stderr = proc.communicate()
    if proc.returncode != 0:
        if proc_stdout:
            _logger.error(
                "ecflow_client stdout for script %s:\n%s", script, proc_stdout.strip()
            )
        if proc_stderr:
            _logger.error(
                "ecflow_client stderr for script %s:\n%s", script, proc_stderr.strip()
            )
        check_retcode(proc.returncode, what="Abort")
    else:
        if proc_stdout:
            _logger.debug(
                "ecflow_client stdout for script %s:\n%s", script, proc_stdout.strip()
            )
        if proc_stderr:
            _logger.debug(
                "ecflow_client stderr for script %s:\n%s", script, proc_stderr.strip()
            )
