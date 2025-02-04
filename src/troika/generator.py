"""Script header generation logic"""

import logging

from . import ConfigurationError, InvocationError

_logger = logging.getLogger(__name__)


def ignore(value):
    """Ignore the requested directive"""
    return None


class Generator:
    """Base script header generator

    Parameters
    ----------
    directive_prefix: bytes or None
        Prefix for the generated directives, e.g. b"#SBATCH ". If `None`, no
        directives will be generated

    directive_translate: dict[str, bytes]
        Directive translation table. Values can be either `bytes` that are
        formatted using the % operator, or callable objects that are called with
        the value of the directive and should return `None` (ignore the
        directive), a byte string, or a list of byte strings

    unknown_directive: str, optional (`'fail'`, `'warn'`, or `'ignore'`)
        If set to `'fail'`, an unknown directive will cause Troika to exit with
        an error. If `'warn'` (the default), a warning will be shown and
        execution will continue. If `'ignore'`, execution will continue without
        warning.
    """

    def __init__(self, directive_prefix, directive_translate, unknown_directive="warn"):
        self.dir_prefix = directive_prefix
        self.dir_translate = directive_translate
        if unknown_directive not in ("fail", "warn", "ignore"):
            raise ConfigurationError(
                f"Invalid unknown directive behaviour: {unknown_directive!r},"
                + "should be 'fail', 'warn', or 'ignore'"
            )
        self.unknown = unknown_directive

    def generate(self, script_data):
        """Generate the script header

        Parameters
        ----------
        script_data: dict
            Script data collected at the parsing stage

        Returns
        -------
        list
            Lines of the script header, with endings
        """

        header = []

        shebang = script_data.get("shebang")
        if shebang is not None:
            if not shebang.endswith(b"\n"):
                shebang += b"\n"
            header.append(shebang)

        if self.dir_prefix is not None:
            for name, arg in script_data["directives"].items():
                fmt = self.dir_translate.get(name)
                if fmt is None:
                    self._unknown_directive(name)
                    continue
                directives = None
                if isinstance(fmt, bytes):
                    directives = [fmt % arg]
                else:
                    directives = fmt(arg)
                    if directives is None:
                        directives = []
                    elif isinstance(directives, bytes):
                        directives = [directives]
                header.extend(
                    self.dir_prefix + directive + b"\n" for directive in directives
                )

        native = script_data.get("native")
        if native is not None:
            for _, directive in native.values():
                header.append(directive)

        extra = script_data.get("extra")
        if extra is not None:
            header.append(b"\n")
            header.extend(extra)

        return header

    def _unknown_directive(self, name):
        if self.unknown == "fail":
            raise InvocationError(f"Unknown directive {name!r}")
        if self.unknown == "warn":
            _logger.warning("Unknown directive %r", name)
