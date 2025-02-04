"""Configuration file handling"""

import logging
import os
from collections import UserDict

import yaml

from . import ConfigurationError, InvocationError
from .utils import first_not_none

_logger = logging.getLogger(__name__)


class Config(UserDict):
    """Configuration mapping"""

    def get_site_config(self, name):
        """Get the configuration associated with the given site

        Parameters
        ----------
        name: str
            Name of the requested site

        Raises
        ------
        `ConfigurationError`
            if the configuration does not define a 'sites' object
        `KeyError`
            if the requested site is not defined
        """
        try:
            sites = self.data["sites"]
        except KeyError:
            raise ConfigurationError("No 'sites' defined in configuration")

        return sites[name]


def get_config(configfile=None, guesses=[]):
    """Read a configuration file

    If configfile is None, the path is read from the ``TROIKA_CONFIG_FILE``
    environment variable, or optional guesses.

    Parameters
    ----------
    configfile: None, path-like or file-like
        Configuration file (path or stream)
    guesses: list of path-like
        Try these paths as a last resort

    Returns
    -------
    `Config`
    """

    configfile = first_not_none(
        [
            configfile,
            os.environ.get("TROIKA_CONFIG_FILE"),
        ]
        + [guess for guess in guesses if os.path.exists(guess)]
    )
    if configfile is None:
        raise InvocationError("No configuration file found")

    try:
        path = os.fspath(configfile)
    except TypeError:  # not path-like
        pass
    else:
        configfile = open(path, "r")

    config_fname = configfile.name if hasattr(configfile, "name") else repr(configfile)
    _logger.debug("Using configuration file %s", config_fname)

    try:
        return Config(yaml.safe_load(configfile))
    except yaml.YAMLError as e:
        raise ConfigurationError(str(e))
