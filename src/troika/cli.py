"""Command-line interface"""

import argparse
import getpass
import logging
import textwrap

from . import log
from . import VERSION, ConfigurationError, InvocationError, RunError
from .config import get_config
from . import hook
from .site import get_site, list_sites
from .utils import ConcurrencyLimit

_logger = logging.getLogger(__name__)


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
            self.logfile = log.get_logfile_path(args.action, getattr(args, 'script', None))
        if args.logfile is not None:
            self.logfile = args.logfile
        log.config(args.verbose - args.quiet, self.logfile)
        self.args = args

    def execute(self):
        """Execute the action"""
        try:
            config = get_config(self.args.config)
            return self.run(config)
        except ConfigurationError as e:
            _logger.critical("Configuration error: %s", e)
            return 1
        except InvocationError as e:
            _logger.critical("Invocation error: %s", e)
            return 1
        except RunError as e:
            _logger.critical("%s", e)
            return 1
        except:
            _logger.exception("Unhandled exception")
            return 1

    def run(self, config):
        """Main entry point for the action

        Parameters
        ----------
        config: `troika.config.Config`

        Returns
        -------
        int
            Exit code
        """
        raise NotImplementedError


class LimitedMixin:
    """Add a concurrency limit to the action"""

    def run(self, config):
        limit = config.get("concurrency_limit", 0)
        with ConcurrencyLimit(limit):
            return super().run(config)


class SiteAction(Action):
    """Action linked to a site"""

    def run(self, config):
        """See `Action.run`"""
        site = get_site(config, self.args.site, self.args.user)
        hook.setup_hooks(config, self.args.site)
        sts = self.site_run(site)
        hook.at_exit(self.args.action, site, self.args, sts, self.logfile)
        return sts

    def site_run(self, site):
        """Main entry point for the site action

        Parameters
        ----------
        site: `troika.site.Site`

        Returns
        -------
        int
            Exit code
        """
        raise NotImplementedError


class SubmitAction(LimitedMixin, SiteAction):
    """Main entry point for the 'submit' sub-command"""
    def site_run(self, site):
        args = self.args
        pp_script = site.preprocess(args.script, args.user, args.output)
        hook.pre_submit(site, args.output, args.dryrun)
        site.submit(pp_script, args.user, args.output, args.dryrun)
        return 0


class MonitorAction(LimitedMixin, SiteAction):
    """Main entry point for the 'monitor' sub-command"""
    def site_run(self, site):
        args = self.args
        site.monitor(args.script, args.user, args.jobid, args.dryrun)
        return 0


class KillAction(LimitedMixin, SiteAction):
    """Main entry point for the 'kill' sub-command"""
    def site_run(self, site):
        args = self.args
        site.kill(args.script, args.user, args.jobid, args.dryrun)
        return 0


class ListSitesAction(Action):
    """Main entry point for the 'list-sites' sub-command"""

    save_log = False

    def run(self, config):
        print("Available sites:")
        print("{name:<28s} {tp:<15s} {conn:<15s}".format(
            name="Name", tp="Type", conn="Connection"))
        print("-" * 60)
        for name, tp, conn in list_sites(config):
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

    epilog = textwrap.dedent("""\
        environment variables:
          TROIKA_CONFIG_FILE    path to the default configuration file
    """)

    default_user = getpass.getuser()

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
    parser.add_argument("-l", "--logfile", default=None,
        help="save log output to this file")

    parser.add_argument("-c", "--config", type=argparse.FileType("r"),
        default=None, help="path to the configuration file")
    parser.add_argument("-n", "--dryrun", default=False,
        action="store_true", help="if true, do not execute, just report")

    subparsers = parser.add_subparsers(
        dest="action", metavar="action",
        help="perform this action, see `%(prog)s <action> --help` for details")

    parser_submit = subparsers.add_parser("submit", help="submit a new job")
    parser_submit.set_defaults(act=SubmitAction)
    parser_submit.add_argument("site", help="target site")
    parser_submit.add_argument("script", help="job script")
    parser_submit.add_argument("-u", "--user", default=default_user,
        help="remote user")
    parser_submit.add_argument("-o", "--output", required=True,
        help="job output file")

    parser_monitor = subparsers.add_parser("monitor",
            help="monitor a submitted job")
    parser_monitor.set_defaults(act=MonitorAction)
    parser_monitor.add_argument("site", help="target site")
    parser_monitor.add_argument("script", help="job script")
    parser_monitor.add_argument("-u", "--user", default=default_user,
        help="remote user")
    parser_monitor.add_argument("-j", "--jobid", default=None,
        help="remote job ID")

    parser_kill = subparsers.add_parser("kill", help="kill a submitted job")
    parser_kill.set_defaults(act=KillAction)
    parser_kill.add_argument("site", help="target site")
    parser_kill.add_argument("script", help="job script")
    parser_kill.add_argument("-u", "--user", default=getpass.getuser(),
        help="remote user")
    parser_kill.add_argument("-j", "--jobid", default=None,
        help="remote job ID")

    parser_listsites = subparsers.add_parser("list-sites",
        help="list available sites")
    parser_listsites.set_defaults(act=ListSitesAction)

    args = parser.parse_args(args)

    if not hasattr(args, 'act'):
        parser.error("please specify an action")

    action = args.act(args)
    return action.execute()
