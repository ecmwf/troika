"""Common hooks"""

import pathlib

from .. import RunError
from .base import pre_submit, at_exit


@pre_submit.register
def create_output_dir(site, output, dryrun=False):
    """Pre-submit hook to create the output directory"""
    out_dir = pathlib.Path(output).parent
    proc = site._connection.execute(["mkdir", "-p", out_dir], dryrun=dryrun)
    if dryrun:
        return
    retcode = proc.wait()
    if retcode != 0:
        msg = "Output directory creation "
        if retcode > 0:
            msg += f"failed with exit code {retcode}"
        else:
            msg += f"terminated by signal {-retcode}"
        raise RunError(msg)


@at_exit.register
def copy_submit_logfile(action, site, args, sts, logfile):
    """Exit hook to copy the log file to the remote server when submitting a job"""
    if action != "submit":
        return
    out_dir = pathlib.Path(args.output).parent
    site._connection.sendfile(logfile, out_dir, dryrun=args.dryrun)
