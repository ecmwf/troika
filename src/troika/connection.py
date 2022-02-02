"""Abstraction of the way to connect to a host"""

import logging
from subprocess import DEVNULL, STDOUT, PIPE  # export for convenience

from . import ConfigurationError
from .components import discover
from . import connections
from .connections.base import Connection

_logger = logging.getLogger(__name__)


def get_connection(name, config, user, plugins):
    known_types = discover(connections, plugins, Connection, attrname="__type_name__")
    _logger.debug("Available connection types: %s", ", ".join(known_types.keys()))

    try:
       cls = known_types[name]
    except KeyError:
        raise ConfigurationError(f"Unknown connection {name!r}")

    conn = cls(config, user)
    _logger.debug("Created connection %r", conn)
    return conn
