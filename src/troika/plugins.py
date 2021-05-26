"""Plugin discovery utilities"""

import importlib
import inspect
import logging
import pkgutil

_logger = logging.getLogger(__name__)


def discover_modules(package, what="plugin"):
    """Discover plugin modules

    Parameters
    ----------
    package: `types.ModuleType`
        Namespace package containing the plugins
    what: str
        String describing what is supposed to be discovered

    Yields
    ------
    (fullname, module)
    fullname: str
        Fully qualified module name
    module: `types.ModuleType`
        Imported module
    """
    path = package.__path__
    prefix = package.__name__ + "."

    _logger.debug(f"{what.capitalize()} search path: %r", path)

    for finder, mname, ispkg in pkgutil.iter_modules(path):
        fullname = prefix + mname
        _logger.debug("Loading module %r", fullname)
        try:
            mod = importlib.import_module(fullname)
        except:
            _logger.warning("Could not load %r", fullname, exc_info=True)
            continue
        yield fullname, mod


def _get_name(cname, cls, suffix, attrname="__plugin_name__"):
    # __dict__ vs. getattr: do not inherit the attribute from a parent class
    name = getattr(cls, "__dict__", {}).get(attrname, None)
    if name is not None:
        return name
    name = cname.lower()
    if name.endswith(suffix):
        name = name[:-len(suffix)]
    return name


def discover(package, base, attrname="__plugin_name__"):
    """Discover plugin classes

    Plugin classes are discovered in a given namespace package, as instance of
    a given base class. The base class itself is ignored, as are classes
    imported from another module (based on ``cls.__module__``). Each discovered
    class is identified by a name that is either the value of attribute
    ``attrname`` if present, or deduced from the class name by changing it to
    lowercase and stripping the name of the base class, if it appears as a
    suffix.

    Parameters
    ----------
    package: `types.ModuleType`
        Namespace package containing the plugins
    base: type
        Base class for the plugins
    attrname: str
        Name of the attribute that conains the name for the plugin

    Returns
    -------
    dict of str: type
        Discovered plugin classes
    """
    what = base.__name__

    def pred(x):
        return inspect.isclass(x) and issubclass(x, base) and x is not base

    discovered = {}
    for fullname, mod in discover_modules(package, what=what):
        for cname, cls in inspect.getmembers(mod, pred):
            tname = _get_name(cname, cls, what.lower(), attrname=attrname)
            if cls.__module__ != fullname:
                _logger.debug(f"Skipping {what.lower()} %r imported by %r", tname, fullname)
                continue
            if tname in discovered:
                _logger.warning(f"{what.capitalize()} type %r is defined more than once", tname)
                continue
            discovered[tname] = cls
    return discovered
