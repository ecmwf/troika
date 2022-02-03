"""Component discovery utilities"""

from importlib.metadata import entry_points


def get_entrypoint(group, name):
    """Load a component from a declared entry point

    Parameters
    ----------
    group: str
        Name of the entry point group, e.g. "troika.controllers"
    name: str
        Name of the component

    Returns
    -------
    module or object
        Component

    Raises
    ------
    KeyError
        If `group` is not found
    ValueError
        If `name` is not found in `group`
    """
    components = entry_points()[group]
    found = [comp for comp in components if comp.name == name]
    if not found:
        raise ValueError(f"Component {name!r} not found in group {group!r}")
    return found[0].load()
