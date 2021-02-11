"""Sites handling"""

import importlib
import inspect
import logging
import pkgutil

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
        _logger.debug("Loading module %r", prefix + name)
        try:
            mod = importlib.import_module(prefix + name)
        except:
            _logger.warning("Could not load %r", name, exc_info=True)
            continue

        for cname, cls in inspect.getmembers(mod, _is_site):
            tname = _site_type_name(cname, cls)
            if tname in discovered:
                _logger.warning("Site type %r is defined more than once", tname)
                continue
            discovered[tname] = cls
    return discovered


def get_site(config, name):
    """Create a `troika.site.Site` object from configuration"""
    known_sites = _discover_sites()
    _logger.debug("Available sites: %s", ", ".join(known_sites.keys()))
    sites = config['sites']
    site_config = sites[name]
    tp = site_config['type']
    cls = known_sites[tp]
    site = cls(site_config)
    _logger.debug("Created %r for %s", site, name)
    return site
