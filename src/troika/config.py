"""Configuration file handling"""

import logging
import os
import yaml

_logger = logging.getLogger(__name__)

def get_config(configfile=None):
    """Read a configuration file

    If configfile is None, the path is read from the ``TROIKA_CONFIG_FILE``
    environment variable.

    Parameters
    ----------
    configfile: None, path-like or file-like
    """

    if configfile is None:
        configfile = os.environ.get("TROIKA_CONFIG_FILE")
        if configfile is None:
            raise RuntimeError("No configuration file found")

    try:
        path = os.fspath(configfile)
    except TypeError: # not path-like
        pass
    else:
        configfile = open(path, "r")

    config_fname = configfile.name if hasattr(configfile, 'name') \
                                   else repr(configfile)
    _logger.debug("Using configuration file %s", config_fname)

    return yaml.safe_load(configfile)
