"""Common definitions"""

VERSION = "0.2.0"


class ConfigurationError(RuntimeError):
    """Exception raised in case of an invalid configuration"""
    pass


class InvocationError(RuntimeError):
    """Exception raised in case of an invalid parameter"""
    pass


class RunError(RuntimeError):
    """Exception raised by runtime failures"""
    pass
