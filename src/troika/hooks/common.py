"""Common hooks"""

import logging
import pathlib

_logger = logging.getLogger(__name__)


def ensure_output_dir(site, output, dryrun=False):
    """Ensure the output directory exists and return its path"""
    return site.create_output_dir(output, dryrun=dryrun)


def remove_previous_output(site, script, output, dryrun=False):
    """Pre-submit hook to potentially previous output"""
    return site.remove_previous_output(output, dryrun=dryrun)


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
