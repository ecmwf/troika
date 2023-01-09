"""Main controller"""

import logging

from . import ConfigurationError
from .components import get_entrypoint

_logger = logging.getLogger(__name__)


def get_controller(config, args, logfile):
    """Create a `troika.controllers.base.Controller` object from configuration"""

    ctl = config.get("controller", "base")
    try:
        cls = get_entrypoint("troika.controllers", ctl)
    except ValueError:
        raise ConfigurationError(f"Unknown controller {ctl!r}")

    ctl = cls(config, args, logfile)
    _logger.debug("Using %r", ctl)
    return ctl
