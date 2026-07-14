"""Site group class"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .. import RunError
from ..site import get_site
from .base import Site

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..config import Config
    from ..connections.base import Connection
    from .base import StrPath

_logger = logging.getLogger(__name__)


class SiteGroup(Site):
    """Site group: choose the first site available"""

    __type_name__ = "group"

    def __init__(self, config: Mapping[str, Any], connection: Connection, global_config: Config) -> None:
        self._select(config, connection.user, global_config)
        self._connection = self._selected._connection

    def _select(self, config: Mapping[str, Any], user: str | None, global_config: Config) -> None:
        """Find a suitable site"""
        sites = config.get("sites", [])
        for name in sites:
            _logger.debug("Trying site %r", name)
            site = get_site(global_config, name, user)
            if self._check(site):
                self._selected = site
                break
        else:
            raise RunError("No site available in the group")

    def _check(self, site: Site) -> bool:
        """Check whether a given site is suitable"""
        return site.check_connection()

    def preprocess(self, script: StrPath, user: str | None, output: StrPath) -> Any:
        """See `troika.sites.base.Site.preprocess`"""
        # NOTE: no Site class defines `preprocess` -- see latent_bugs.md (#1).
        return self._selected.preprocess(script, user, output)  # type: ignore[attr-defined]

    def submit(self, script: StrPath, user: str | None, output: StrPath, dryrun: bool = False) -> Any:
        """See `troika.sites.base.Site.submit`"""
        return self._selected.submit(script, user, output, dryrun=dryrun)

    def monitor(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> None:
        """See `troika.sites.base.Site.monitor`"""
        return self._selected.monitor(script, user, output=output, jid=jid, dryrun=dryrun)

    def kill(
        self,
        script: StrPath,
        user: str | None,
        output: StrPath | None = None,
        jid: str | None = None,
        dryrun: bool = False,
    ) -> tuple[int | str, str | None]:
        """See `troika.sites.base.Site.kill`"""
        return self._selected.kill(script, user, output=output, jid=jid, dryrun=dryrun)

    def check_connection(self, timeout: int | None = None, dryrun: bool = False) -> bool:
        """See `troika.sites.base.Site.check_connection`"""
        return self._selected.check_connection(timeout=timeout, dryrun=dryrun)
