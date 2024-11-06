"""Command-line interface"""

import argparse
import logging
import pathlib
import sys
import textwrap

from . import VERSION, ConfigurationError, InvocationError, RunError, log
from .config import get_config
from .controller import get_controller

_logger = logging.getLogger(__name__)

_config_guesses = [
    p / "etc" / "troika.yml"
    for p in [
        pathlib.Path(__file__).parent.parent.parent.parent.parent,
        pathlib.Path(sys.prefix),
    ]
]


class Action:
    """Command-line action

    Parameters
    ----------
    args: `argparse.Namespace`-like
    """

    #: If True, write the logs to a file
    save_log = True

    def __init__(self, args):
        self.logfile = None
        if self.save_log:
            self.logfile = log.get_logfile_path(
                args.action, getattr(args, "script", None)
            )
        if args.logfile is not None:
            self.logfile = args.logfile
        self.logmode = "a" if args.append_log else "w"
        log.config(args.verbose - args.quiet, self.logfile, self.logmode)
        self.args = args

    def execute(self):
        """Execute the action"""
        try:
            config = get_config(self.args.config, guesses=_config_guesses)
            controller = get_controller(config, self.args, self.logfile)
            return self.run(config, controller)
        except ConfigurationError as e:
            _logger.critical("Configuration error: %s", e)
            return 1
        except InvocationError as e:
            _logger.critical("Invocation error: %s", e)
            return 1
        except RunError as e:
            _logger.critical("%s", e)
            return 1
        except Exception:
            _logger.exception("Unhandled exception")
            return 1

    def run(self, config, controller):
        """Main entry point for the action

        Parameters
        ----------
        config: `troika.config.Config`
        controller: `troika.controller.Controller`

        Returns
        -------
        int
            Exit code
        """
        raise NotImplementedError


class SubmitAction(Action):
    """Main entry point for the 'submit' sub-command"""

    def run(self, config, controller):
        args = self.args
        return controller.submit(args.script, args.user, args.output, args.dryrun)


class MonitorAction(Action):
    """Main entry point for the 'monitor' sub-command"""

    def run(self, config, controller):
        args = self.args
        return controller.monitor(
            args.script, args.user, args.output, args.jobid, args.dryrun
        )


class KillAction(Action):
    """Main entry point for the 'kill' sub-command"""

    def run(self, config, controller):
        args = self.args
        return controller.kill(
            args.script, args.user, args.output, args.jobid, args.dryrun
        )


class CheckConnectionAction(Action):
    """Main entry point for the 'check-connection' sub-command"""

    save_log = False

    def run(self, config, controller):
        args = self.args
        working = controller.check_connection(args.timeout, args.dryrun)
        if working:
            print("OK")
            return 0
        print("Connection failed", file=sys.stderr)
        return 1


class ListSitesAction(Action):
    """Main entry point for the 'list-sites' sub-command"""

    save_log = False

    def run(self, config, controller):
        print("Available sites:")
        print(
            "{name:<28s} {tp:<15s} {conn:<15s}".format(
                name="Name", tp="Type", conn="Connection"
            )
        )
        print("-" * 60)
        for name, tp, conn in controller.list_sites():
            print(f"{name:<28s} {tp:<15s} {conn:<15s}")
        return 0


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

    epilog = textwrap.dedent(
        """\
        environment variables:
          TROIKA_CONFIG_FILE    path to the default configuration file
    """
    )

    parser = argparse.ArgumentParser(
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Submit, monitor and kill jobs on remote systems",
        epilog=epilog,
    )

    parser.add_argument(
        "-V", "--version", action="version", version=("%(prog)s " + VERSION)
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase verbosity level (can be repeated)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="decrease verbosity level (can be repeated)",
    )
    parser.add_argument(
        "-l", "--logfile", default=None, help="save log output to this file"
    )
    parser.add_argument(
        "-A",
        "--append-log",
        default=False,
        action="store_true",
        help="append to the log file instead of overwriting",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=argparse.FileType("r"),
        default=None,
        help="path to the configuration file",
    )
    parser.add_argument(
        "-n",
        "--dryrun",
        default=False,
        action="store_true",
        help="if true, do not execute, just report",
    )

    subparsers = parser.add_subparsers(
        dest="action",
        metavar="action",
        help="perform this action, see `%(prog)s <action> --help` for details",
    )

    parser_submit = subparsers.add_parser("submit", help="submit a new job")
    parser_submit.set_defaults(act=SubmitAction)
    parser_submit.add_argument("site", help="target site")
    parser_submit.add_argument("script", help="job script")
    parser_submit.add_argument("-u", "--user", default=None, help="remote user")
    parser_submit.add_argument("-o", "--output", required=True, help="job output file")
    parser_submit.add_argument(
        "-D",
        "--define",
        default=[],
        action="append",
        metavar="NAME=VALUE",
        help="set these directives in the submitted job",
    )

    parser_monitor = subparsers.add_parser("monitor", help="monitor a submitted job")
    parser_monitor.set_defaults(act=MonitorAction)
    parser_monitor.add_argument("site", help="target site")
    parser_monitor.add_argument("script", help="job script")
    parser_monitor.add_argument("-u", "--user", default=None, help="remote user")
    parser_monitor.add_argument(
        "-o", "--output", required=False, help="job output file"
    )
    parser_monitor.add_argument(
        "-j",
        "--jobid",
        default=None,
        type=lambda j: None if j == "" else j,
        help="remote job ID",
    )

    parser_kill = subparsers.add_parser("kill", help="kill a submitted job")
    parser_kill.set_defaults(act=KillAction)
    parser_kill.add_argument("site", help="target site")
    parser_kill.add_argument("script", help="job script")
    parser_kill.add_argument("-u", "--user", default=None, help="remote user")
    parser_kill.add_argument("-o", "--output", required=False, help="job output file")
    parser_kill.add_argument(
        "-j",
        "--jobid",
        default=None,
        type=lambda j: None if j == "" else j,
        help="remote job ID",
    )

    parser_checkconn = subparsers.add_parser(
        "check-connection", help="check whether the connection works"
    )
    parser_checkconn.set_defaults(act=CheckConnectionAction)
    parser_checkconn.add_argument("site", help="target site")
    parser_checkconn.add_argument("-u", "--user", default=None, help="remote user")
    parser_checkconn.add_argument(
        "-t",
        "--timeout",
        default=None,
        type=int,
        help="wait at most this number of seconds",
    )

    parser_listsites = subparsers.add_parser("list-sites", help="list available sites")
    parser_listsites.set_defaults(act=ListSitesAction)

    args = parser.parse_args(args)

    if not hasattr(args, "act"):
        parser.error("please specify an action")

    action = args.act(args)
    return action.execute()
