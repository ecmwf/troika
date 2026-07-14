"""Abstraction of the way to connect to a host"""

from __future__ import annotations

import logging
from subprocess import DEVNULL, PIPE, STDOUT  # noqa
from typing import TYPE_CHECKING, Any

from . import ConfigurationError
from .components import get_entrypoint

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .connections.base import Connection

_logger = logging.getLogger(__name__)


def get_connection(name: str, config: Mapping[str, Any], user: str | None) -> Connection:
    """Load the requested `troika.connections.base.Connection` object"""

    try:
        cls = get_entrypoint("troika.connections", name)
    except ValueError:
        raise ConfigurationError(f"Unknown connection {name!r}")

    conn: Connection = cls(config, user)
    _logger.debug("Created connection %r", conn)
    return conn
