"""Common definitions"""

VERSION = "0.0.1"


class ConfigurationError(RuntimeError):
    """Exception raised in case of an invalid configuration"""
    pass


class InvocationError(RuntimeError):
    """Exception raised in case of an invalid parameter"""
    pass
