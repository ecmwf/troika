"""Sites handling"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from . import ConfigurationError, InvocationError
from .components import get_entrypoint
from .connection import get_connection

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .config import Config
    from .sites.base import Site

_logger = logging.getLogger(__name__)


def get_site(config: Config, name: str, user: str | None) -> Site:
    """Create a `troika.site.Site` object from configuration"""

    try:
        site_config = config.get_site_config(name)
    except KeyError:
        raise InvocationError(f"Unknown site {name!r}")

    try:
        tp = site_config["type"]
    except KeyError:
        raise ConfigurationError(f"Site {name!r} has no 'type'")

    try:
        cls = get_entrypoint("troika.sites", tp)
    except ValueError:
        raise ConfigurationError(f"Site {name!r} has unknown type {tp!r}")

    try:
        conn_name = site_config["connection"]
    except KeyError:
        raise ConfigurationError(f"Site {name!r} has no 'connection'")

    conn = get_connection(conn_name, site_config, user)
    site = cls(site_config, conn, config)
    _logger.debug("Created %r for %s", site, name)
    return site


def list_sites(config: Config) -> Iterator[tuple[str, Any, Any]]:
    """List available sites

    Parameters
    ----------
    config: `troika.config.Config`
        Configuration object

    Yields
    -------
    ``(name, type, connection)``
    """
    try:
        sites = config["sites"]
    except KeyError:
        raise ConfigurationError("No 'sites' defined in configuration")

    for name, site in sites.items():
        try:
            tp = site["type"]
        except KeyError:
            raise ConfigurationError(f"Site {name!r} has no 'type'")
        try:
            conn = site["connection"]
        except KeyError:
            raise ConfigurationError(f"Site {name!r} has no 'connection'")
        yield name, tp, conn
