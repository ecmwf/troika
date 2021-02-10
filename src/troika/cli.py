"""Command-line interface"""

import argparse
import logging
import textwrap

from . import log
from . import VERSION
from .config import get_config
from .sites import get_site

_logger = logging.getLogger(__name__)


def submit(site, args):
    """Main entry point for the 'submit' sub-command

    Parameters
    ----------
    site: `troika.site.Site`
    args: `argparse.Namespace`-like

    Returns
    -------
    int
        Exit code
    """

    site.submit(args.script, args.user, args.output, args.dryrun)

    return 0


def monitor(site, args):
    """Main entry point for the 'monitor' sub-command

    Parameters
    ----------
    site: `troika.site.Site`
    args: `argparse.Namespace`-like

    Returns
    -------
    int
        Exit code
    """

    _logger.error("monitor: not implemented")
    return 1


def kill(site, args):
    """Main entry point for the 'kill' sub-command

    Parameters
    ----------
    site: `troika.site.Site`
    args: `argparse.Namespace`-like

    Returns
    -------
    int
        Exit code
    """

    _logger.error("kill: not implemented")
    return 1


def main(args=None, prog=None):
    """Main entry point

    Parameters
    ----------
    args: None or list of str
        Use these command-line arguments instead of sys.argv
    prog: None or str
        Use this program name

    Returns
    -------
    int
        Exit code
    """

    epilog = textwrap.dedent("""\
        environment variables:
          TROIKA_CONFIG_FILE    path to the default configuration file
    """)

    parser = argparse.ArgumentParser(
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Submit, monitor and kill jobs on remote systems",
        epilog=epilog)

    parser.add_argument("-V", "--version", action="version",
        version=("%(prog)s " + VERSION))

    parser.add_argument("-v", "--verbose", action="count", default=0,
        help="increase verbosity level (can be repeated)")
    parser.add_argument("-q", "--quiet", action="count", default=0,
        help="decrease verbosity level (can be repeated)")

    parser.add_argument("-c", "--config", type=argparse.FileType("r"),
        default=None, help="path to the configuration file")
    parser.add_argument("-n", "--dryrun", default=False,
        action="store_true", help="if true, do not execute, just report")

    subparsers = parser.add_subparsers(
        metavar="action",
        help="perform this action, see `%(prog)s <action> --help` for details")

    parser_submit = subparsers.add_parser("submit", help="submit a new job")
    parser_submit.set_defaults(func=submit)
    parser_submit.add_argument("site", help="target site")
    parser_submit.add_argument("script", help="job script")
    parser_submit.add_argument("-u", "--user", required=True,
        help="remote user")
    parser_submit.add_argument("-o", "--output", required=True,
        help="job output file")

    parser_monitor = subparsers.add_parser("monitor",
            help="monitor a submitted job")
    parser_monitor.set_defaults(func=monitor)
    parser_monitor.add_argument("site", help="target site")

    parser_kill = subparsers.add_parser("kill", help="kill a submitted job")
    parser_kill.set_defaults(func=kill)
    parser_monitor.add_argument("site", help="target site")

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.error("please specify an action")

    log.config(args.verbose - args.quiet)

    try:
        config = get_config(args.config)
        site = get_site(config, args.site)
        return args.func(site, args)
    except:
        _logger.exception("Unhandled exception")
        return 1
