"""Plugin discovery and loading utilities"""

import importlib
import logging

from . import ConfigurationError, RunError

_logger = logging.getLogger(__name__)


MODULE_PREFIX = "troika.plugins."


def load_plugins(names):
    """Load the given plugins

    Parameters
    ----------
    names: list[str]
        Name of the plugins to load

    Returns
    -------
    list[(str, module)]
        Loaded plugins

    Raises
    ------
    `troika.ConfigurationError`
        If a plugin does not exist or raises an ImportError
    `troika.RunError`
        If a plugin raises another error
    """
    plugins = []
    for name in names:
        fullname = MODULE_PREFIX + name
        _logger.debug("Loading %r", name)
        try:
            mod = importlib.import_module(fullname)
        except ImportError as e:
            raise ConfigurationError(f"Cannot load plugin {name!r}: {e!s}") from e
        except Exception as e:
            raise RunError("Error when loading plugin {name!r}: {e!s}") from e
        plugins.append((fullname, mod))
    return plugins
