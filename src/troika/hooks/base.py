"""Base hook definitions"""

import functools
import logging

from .. import ConfigurationError
from ..components import get_entrypoint

_logger = logging.getLogger(__name__)


class Hook:
    """Helper class to manage hooks

    Parameters
    ----------
    name: str
        Hook name
    """

    #: Entrypoint namespace
    _namespace = "troika.hooks"

    registered_hooks = {}

    @classmethod
    def declare(cls, func, name=None):
        """Register a hook

        Parameters
        ----------
        func: callable
            Hook specification function (code is discarded)
        name: str or None
            Name of the hook (default: ``func.__name__``)
        """
        if name is None:
            name = func.__name__
        hook = cls(name)
        functools.update_wrapper(hook, func)
        cls.registered_hooks[name] = hook
        return hook

    def __init__(self, name):
        self.name = name
        self._hooks = {}
        self._impl = None

    def __call__(self, *args, **kwargs):
        if self._impl is None:
            raise ValueError("Attempt to call a non-instantiated hook registry")
        _logger.debug("Executing %s hooks", self.name)
        results = []
        for funcname, func in self._impl:
            _logger.debug("Calling hook function %s", funcname)
            res = func(*args, **kwargs)
            results.append(res)
        return results

    def instantiate(self, hooks):
        """Select the requested hook implementations

        Parameters
        ----------
        hooks: list of str
            Requested hooks
        """
        hookfuncs = []
        for hookname in hooks:
            try:
                hookfunc = get_entrypoint(f"{self._namespace}.{self.name}", hookname)
            except ValueError:
                msg = f"Implementation {hookname!r} not found for {self.name} hook"
                raise ConfigurationError(msg)
            hookfuncs.append((hookname, hookfunc))
        self._impl = hookfuncs


@Hook.declare
def at_startup(action, site, args):
    """Startup hook

    Parameters
    ----------
    action: {"submit", "monitor", "kill"}
        Action that was requested
    site: :py:class:`troika.sites.base.Site`
        Selected site
    args: :py:class:`argparse.Namespace`-like
        Command-line arguments

    Returns
    -------
    bool
        If True, interrupt the action
    """


@Hook.declare
def pre_submit(site, script, output, dryrun):
    """Pre-submit hook

    Parameters
    ----------
    site: :py:class:`troika.sites.base.Site`
        Selected site
    script: path-like
        Path to the script to be submitted
    output: path-like
        Path to the job output file
    dryrun: bool
        If True, do not do anything, only print actions
    """


@Hook.declare
def post_kill(site, script, output, jid, cancel_status, dryrun):
    """Post-kill hook

    Parameters
    ----------
    site: :py:class:`troika.sites.base.Site`
        Selected site
    script: path-like
        Path to the script file of the job being killed
    output: path-like or None
        Path to the job output file
    jid: str
        Job ID of the job being killed
    cancel_status: str
        CANCELLED, KILLED or TERMINATED
    dryrun: bool
        If True, do not do anything, only print actions
    """


@Hook.declare
def at_exit(action, site, args, sts, logfile):
    """Exit hook

    Parameters
    ----------
    action: {"submit", "monitor", "kill"}
        Action that was requested
    site: :py:class:`troika.sites.base.Site`
        Selected site
    args: :py:class:`argparse.Namespace`-like
        Command-line arguments
    sts: int
        Exit status
    logfile: path-like
        Path to the log file
    """
