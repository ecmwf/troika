"""Abstraction of the way to connect to a host"""

import logging
from subprocess import DEVNULL, PIPE, STDOUT  # noqa

from . import ConfigurationError
from .components import get_entrypoint

_logger = logging.getLogger(__name__)


def get_connection(name, config, user):
    """Load the requested `troika.connections.base.Connection` object"""

    try:
        cls = get_entrypoint("troika.connections", name)
    except ValueError:
        raise ConfigurationError(f"Unknown connection {name!r}")

    conn = cls(config, user)
    _logger.debug("Created connection %r", conn)
    return conn
