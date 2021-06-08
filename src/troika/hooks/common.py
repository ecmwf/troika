"""Common hooks"""

import pathlib

from ..utils import check_retcode
from .base import pre_submit, at_exit


@pre_submit.register
def create_output_dir(site, output, dryrun=False):
    """Pre-submit hook to create the output directory"""
    out_dir = pathlib.Path(output).parent
    proc = site._connection.execute(["mkdir", "-p", out_dir], dryrun=dryrun)
    if dryrun:
        return
    retcode = proc.wait()
    check_retcode(retcode, what="Output directory creation")


@at_exit.register
def copy_submit_logfile(action, site, args, sts, logfile):
    """Exit hook to copy the log file to the remote server when submitting a job"""
    if action != "submit":
        return
    out_dir = pathlib.Path(args.output).parent
    site._connection.sendfile(logfile, out_dir, dryrun=args.dryrun)
