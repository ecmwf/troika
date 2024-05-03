"""Translators that operate on resources"""


def enable_hyperthreading(script_data, global_config, site):
    """Add the 'enable_hyperthreading' directive when needed"""
    enable = int(script_data["directives"].get("threads_per_core", 1)) > 1
    script_data["directives"].setdefault("enable_hyperthreading", enable)
    return script_data
