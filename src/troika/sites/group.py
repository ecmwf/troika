"""Site group class"""

import logging

from .. import RunError
from ..site import get_site
from .base import Site

_logger = logging.getLogger(__name__)


class SiteGroup(Site):
    """Site group: choose the first site available"""

    __type_name__ = "group"

    def __init__(self, config, connection, global_config):
        self._select(config, connection.user, global_config)
        self._connection = self._selected._connection

    def _select(self, config, user, global_config):
        """Find a suitable site"""
        sites = config.get("sites", [])
        self._selected = None
        for name in sites:
            _logger.debug("Trying site %r", name)
            site = get_site(global_config, name, user)
            if self._check(site):
                self._selected = site
                break
        if self._selected is None:
            raise RunError("No site available in the group")

    def _check(self, site):
        """Check whether a given site is suitable"""
        return site.check_connection()

    def preprocess(self, script, user, output):
        """See `troika.sites.base.Site.preprocess`"""
        return self._selected.preprocess(script, user, output)

    def submit(self, script, user, output, dryrun=False):
        """See `troika.sites.base.Site.submit`"""
        return self._selected.submit(script, user, output, dryrun=dryrun)

    def monitor(self, script, user, output=None, jid=None, dryrun=False):
        """See `troika.sites.base.Site.monitor`"""
        return self._selected.monitor(
            script, user, output=output, jid=jid, dryrun=dryrun
        )

    def kill(self, script, user, output=None, jid=None, dryrun=False):
        """See `troika.sites.base.Site.kill`"""
        return self._selected.kill(script, user, output=output, jid=jid, dryrun=dryrun)

    def check_connection(self, timeout=None, dryrun=False):
        """See `troika.sites.base.Site.check_connection`"""
        return self._selected.check_connection(timeout=timeout, dryrun=dryrun)
