"""Main controller"""

import logging

from . import ConfigurationError
from .controllers.base import Controller
from . import controllers
from .plugins import discover

_logger = logging.getLogger(__name__)


def get_controller(config, args, logfile):
    """Create a `troika.controllers.base.Controller` object from configuration"""
    known_types = discover(controllers, Controller, attrname="__type_name__", allow_base=True)
    _logger.debug("Available controllers: %s", ", ".join(known_types.keys()))

    ctl = config.get("controller", "base")
    try:
        cls = known_types[ctl]
    except KeyError:
        raise ConfigurationError(f"Unknown controller {ctl!r}")

    ctl = cls(config, args, logfile)
    _logger.debug("Using %r", ctl)
    return ctl
