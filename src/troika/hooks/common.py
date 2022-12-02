"""Common hooks"""

import logging
import pathlib

from ..connection import PIPE
from ..utils import check_retcode

_logger = logging.getLogger(__name__)


def ensure_output_dir(site, output, dryrun=False):
    """Ensure the output directory exists and return its path"""
    out_dir = pathlib.PurePath(output).parent
    pmkdir_command = site.config.get('pmkdir_command', ['mkdir', '-p'])
    if isinstance(pmkdir_command, (str, bytes)):
        pmkdir_command = [ pmkdir_command ]
    else:
        pmkdir_command = list(pmkdir_command)
    proc = site._connection.execute(pmkdir_command + [out_dir], stdout=PIPE, stderr=PIPE, dryrun=dryrun)
    if dryrun:
        return out_dir
    proc_stdout, proc_stderr = proc.communicate()
    if proc.returncode != 0:
        if proc_stdout: _logger.error("%s stdout:\n%s", pmkdir_command[0], proc_stdout.strip())
        if proc_stderr: _logger.error("%s stderr:\n%s", pmkdir_command[0], proc_stderr.strip())
        check_retcode(proc.returncode, what="Ouput directory creation")
    else:
        if proc_stdout: _logger.debug("%s stdout:\n%s", pmkdir_command[0], proc_stdout.strip())
        if proc_stderr: _logger.debug("%s stderr:\n%s", pmkdir_command[0], proc_stderr.strip())
    return out_dir

def check_connection(action, site, args):
    """Startup hook to check the connection works before doing anything"""
    working = site.check_connection(dryrun=args.dryrun)
    if not working:
        _logger.error("Connection not working. Exiting.")
        return True


def create_output_dir(site, script, output, dryrun=False):
    """Pre-submit hook to create the output directory"""
    ensure_output_dir(site, output, dryrun=dryrun)


def copy_orig_script(site, script, output, dryrun=False):
    """Pre-submit hook to copy the original script to the remote server"""
    out_dir = ensure_output_dir(site, output, dryrun=dryrun)
    script = pathlib.PurePath(script)
    orig_script = script.with_suffix(script.suffix + ".orig")
    site._connection.sendfile(orig_script, out_dir / orig_script.name, dryrun=dryrun)


def copy_submit_logfile(action, site, args, sts, logfile):
    """Exit hook to copy the log file to the remote server when submitting a job"""
    if action != "submit":
        return
    logfile = pathlib.PurePath(logfile)
    out_dir = ensure_output_dir(site, args.output, dryrun=args.dryrun)
    site._connection.sendfile(logfile, out_dir / logfile.name, dryrun=args.dryrun)


def copy_kill_logfile(action, site, args, sts, logfile):
    """Exit hook to copy the log file to the remote server when killing a job"""
    if action != "kill":
        return
    if args.output:
        logfile = pathlib.PurePath(logfile)
        out_dir = ensure_output_dir(site, args.output, dryrun=args.dryrun)
        site._connection.sendfile(logfile, out_dir / logfile.name, dryrun=args.dryrun)
    else:
        _logger.error("copy_kill_logfile hook requires output argument to be passed")
