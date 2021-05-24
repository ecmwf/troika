"""Sites handling"""

import logging

from . import ConfigurationError, InvocationError
from .connection import get_connection
from .plugins import discover
from .sites.base import Site
from . import sites

_logger = logging.getLogger(__name__)


def get_site(config, name, user):
    """Create a `troika.site.Site` object from configuration"""
    known_types = discover(sites, Site, attrname="__type_name__")
    _logger.debug("Available site types: %s", ", ".join(known_types.keys()))

    try:
        site_config = config.get_site_config(name)
    except KeyError:
        raise InvocationError(f"Unknown site {name!r}")

    try:
        tp = site_config['type']
    except KeyError:
        raise ConfigurationError(f"Site {name!r} has no 'type'")

    try:
        cls = known_types[tp]
    except KeyError:
        raise ConfigurationError(f"Site {name!r} has unknown type {tp!r}")

    try:
        conn_name = site_config['connection']
    except KeyError:
        raise ConfigurationError(f"Site {name!r} has no 'connection'")

    conn = get_connection(conn_name, site_config, user)
    site = cls(site_config, conn)
    _logger.debug("Created %r for %s", site, name)
    return site
