"""Common hooks"""

import logging
import pathlib

from ..utils import check_retcode

_logger = logging.getLogger(__name__)


def check_connection(action, site, args):
    """Startup hook to check the connection works before doing anything"""
    working = site.check_connection(dryrun=args.dryrun)
    if not working:
        _logger.error("Connection not working. Exiting.")
        return True


def create_output_dir(site, script, output, dryrun=False):
    """Pre-submit hook to create the output directory"""
    out_dir = pathlib.Path(output).parent
    proc = site._connection.execute(["mkdir", "-p", out_dir], dryrun=dryrun)
    if dryrun:
        return
    retcode = proc.wait()
    check_retcode(retcode, what="Output directory creation")


def copy_orig_script(site, script, output, dryrun=False):
    """Pre-submit hook to copy the original script to the remote server"""
    out_dir = pathlib.Path(output).parent
    script = pathlib.Path(script)
    orig_script = script.with_suffix(script.suffix + ".orig")
    site._connection.sendfile(orig_script, out_dir, dryrun=dryrun)


def copy_submit_logfile(action, site, args, sts, logfile):
    """Exit hook to copy the log file to the remote server when submitting a job"""
    if action != "submit":
        return
    out_dir = pathlib.Path(args.output).parent
    site._connection.sendfile(logfile, out_dir, dryrun=args.dryrun)


def copy_kill_logfile(action, site, args, sts, logfile):
    """Exit hook to copy the log file to the remote server when killing a job"""
    if action != "kill":
        return
    if args.output:
        out_dir = pathlib.Path(args.output).parent
        site._connection.sendfile(logfile, out_dir, dryrun=args.dryrun)
    else:
        _logger.error("copy_kill_logfile hook requires output argument to be passed")
