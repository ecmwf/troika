"""Site group class"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .. import RunError
from ..site import get_site
from .base import Site

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Mapping

    from ..config import Config
    from ..connections.base import Connection
    from ..parser import BaseParser
    from .base import DirectiveValue, StrPath

_logger = logging.getLogger(__name__)


class SiteGroup(Site):
    """Site group: transparently proxy the first available site.

    ``SiteGroup`` implements the :class:`~troika.sites.base.Site` interface by
    forwarding every operation to a selected backend, so it holds no site state
    of its own (and does not extend ``BaseSite``). ``config`` and
    ``_connection`` mirror the selected backend's.
    """

    __type_name__ = "group"

    def __init__(self, config: Mapping[str, Any], connection: Connection, global_config: Config) -> None:
        self._selected = self._select(config, connection.user, global_config)
        self.config = self._selected.config
        self._connection = self._selected._connection

    def _select(self, config: Mapping[str, Any], user: str | None, global_config: Config) -> Site:
        """Find a suitable site"""
        sites = config.get("sites", [])
        for name in sites:
            _logger.debug("Trying site %r", name)
            site = get_site(global_config, name, user)
            if self._check(site):
                return site
        raise RunError("No site available in the group")

    def _check(self, site: Site) -> bool:
        """Check whether a given site is suitable"""
        return site.check_connection()

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

    def create_output_dir(self, output: StrPath, dryrun: bool = False) -> pathlib.PurePath:
        """See `troika.sites.base.Site.create_output_dir`"""
        return self._selected.create_output_dir(output, dryrun=dryrun)

    def get_native_parser(self) -> BaseParser | None:
        """See `troika.sites.base.Site.get_native_parser`"""
        return self._selected.get_native_parser()

    def get_directive_translation(self) -> tuple[bytes | None, dict[str, DirectiveValue]]:
        """See `troika.sites.base.Site.get_directive_translation`"""
        return self._selected.get_directive_translation()

    def remove_previous_output(self, output: StrPath, dryrun: bool = False) -> None:
        """See `troika.sites.base.Site.remove_previous_output`"""
        return self._selected.remove_previous_output(output, dryrun=dryrun)
