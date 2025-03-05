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
    eps = entry_points()
    if hasattr(eps, "select"):  # Python >=3.10
        if group not in eps.groups:
            raise KeyError(group)
        found = eps.select(group=group, name=name)
    else:
        found = [comp for comp in eps[group] if comp.name == name]

    component = next(iter(found), None)
    if component is None:
        raise ValueError(f"Component {name!r} not found in group {group!r}")
    return component.load()
