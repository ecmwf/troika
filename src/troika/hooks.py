"""Hook system to perform custom actions"""

import logging
import os
import pathlib

from . import ConfigurationError, RunError
from .utils import check_status

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


@pre_submit.register
def create_output_dir(site, output, dryrun=False):
    """Pre-submit hook to create the output directory"""
    out_dir = pathlib.Path(output).parent
    pid = site._connection.execute(["mkdir", "-p", out_dir], dryrun=dryrun)
    if dryrun:
        return
    _, sts = os.waitpid(pid, 0)
    retcode = check_status(sts)
    if retcode != 0:
        msg = "Output directory creation "
        if retcode > 0:
            msg += f"failed with exit code {retcode}"
        else:
            msg += f"terminated by signal {-retcode}"
        raise RunError(msg)


def setup_hooks(config, site):
    """Set up the hooks according to site configuration

    Parameters
    ----------
    config: `troika.config.Config`
        Configuration object
    site: str
        Site name
    """
    site_config = config.get_site_config(site)
    for spec in Hook.registered_hooks.values():
        req = site_config.get(spec.name, [])
        spec.instantiate(req)
        if req:
            _logger.debug("Enabled %s hooks: %s", spec.name, ", ".join(req))
