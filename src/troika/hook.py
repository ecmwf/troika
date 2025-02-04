"""Hook system to perform custom actions"""

import logging

from .hooks.base import Hook, at_exit, at_startup, post_kill, pre_submit  # noqa

_logger = logging.getLogger(__name__)


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
