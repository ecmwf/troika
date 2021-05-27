"""Base hook definitions"""

import logging

from .. import ConfigurationError

_logger = logging.getLogger(__name__)


class Hook:
    """Helper class to manage hooks

    Parameters
    ----------
    name: str
        Hook name
    """

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
        for funcname, func in self._impl:
            _logger.debug("Calling hook function %s", funcname)
            func(*args, **kwargs)

    def register(self, func, key=None):
        """Register a function for use as a hook

        Parameters
        ----------
        func: callable
            Hook function
        key: str or None
            If specified, key to use for lookup. If None, the function name
            will be used instead.
        """
        if key is None:
            key = func.__name__
        if key in self._hooks:
            _logger.warning("Multiply defined %r %s hook", key, self.name)
        self._hooks[key] = func
        return func

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
                hookfunc = self._hooks[hookname]
            except KeyError:
                msg = f"Implementation {hookname!r} not found for {self.name} hook"
                raise ConfigurationError(msg)
            hookfuncs.append((hookname, hookfunc))
        self._impl = hookfuncs


@Hook.declare
def pre_submit(site, output, dryrun):
    """Pre-submit hook

    Parameters
    ----------
    site: `troika.sites.base.Site`
        Selected site
    output: path-like
        Path to the job output file
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
    site: `troika.sites.base.Site`
        Selected site
    args: `argparse.Namespace`-like
        Command-line arguments
    sts: int
        Exit status
    logfile: path-like
        Path to the log file
    """