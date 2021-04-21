"""Sites handling"""

import importlib
import inspect
import logging
import pkgutil

from . import ConfigurationError, InvocationError
from .connection import get_connection
from .sites.base import Site
from . import sites

_logger = logging.getLogger(__name__)


def _is_site(x):
    return inspect.isclass(x) and issubclass(x, Site) and x is not Site


def _site_type_name(cname, cls):
    name = getattr(cls, "__type_name__", None)
    if name is not None:
        return name
    name = cname.lower()
    if name.endswith('site'):
        name = name[:-len('site')]
    return name


def _discover_sites():
    path = sites.__path__
    prefix = sites.__name__ + "."
    _logger.debug("Site search path: %r", path)
    discovered = {}
    for finder, name, ispkg in pkgutil.iter_modules(path):
        fullname = prefix + name
        _logger.debug("Loading module %r", fullname)
        try:
            mod = importlib.import_module(fullname)
        except:
            _logger.warning("Could not load %r", name, exc_info=True)
            continue

        for cname, cls in inspect.getmembers(mod, _is_site):
            tname = _site_type_name(cname, cls)
            if cls.__module__ != fullname:
                _logger.debug("Skipping site %r imported by %r", tname, fullname)
                continue
            if tname in discovered:
                _logger.warning("Site type %r is defined more than once", tname)
                continue
            discovered[tname] = cls
    return discovered


def get_site(config, name, user):
    """Create a `troika.site.Site` object from configuration"""
    known_types = _discover_sites()
    _logger.debug("Available site types: %s", ", ".join(known_types.keys()))

    try:
        sites = config['sites']
    except KeyError:
        raise ConfigurationError(f"No 'sites' defined in configuration")

    try:
        site_config = sites[name]
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
