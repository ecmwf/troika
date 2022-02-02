"""Main controller"""

import logging

from . import ConfigurationError
from .components import discover
from .controllers.base import Controller
from . import controllers

_logger = logging.getLogger(__name__)


def get_controller(config, args, logfile, plugins):
    """Create a `troika.controllers.base.Controller` object from configuration"""
    known_types = discover(controllers, plugins, Controller, attrname="__type_name__", allow_base=True)
    _logger.debug("Available controllers: %s", ", ".join(known_types.keys()))

    ctl = config.get("controller", "base")
    try:
        cls = known_types[ctl]
    except KeyError:
        raise ConfigurationError(f"Unknown controller {ctl!r}")

    ctl = cls(config, args, logfile, plugins)
    _logger.debug("Using %r", ctl)
    return ctl
