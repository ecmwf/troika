"""Script header generation logic"""

import logging

from . import ConfigurationError, InvocationError

_logger = logging.getLogger(__name__)


class Generator:
    """Base script header generator

    Parameters
    ----------
    directive_prefix: bytes or None
        Prefix for the generated directives, e.g. b"#SBATCH ". If `None`, no
        directives will be generated

    directive_translate: dict[str, bytes]
        Directive translation table. Values are formatted using the % operator

    unknown_directive: str, optional (`'fail'`, `'warn'`, or `'ignore'`)
        If set to `'fail'`, an unknown directive will cause Troika to exit with
        an error. If `'warn'` (the default), a warning will be shown and
        execution will continue. If `'ignore'`, execution will continue without
        warning.
    """


    def __init__(self, directive_prefix, directive_translate, unknown_directive='warn'):
        self.dir_prefix = directive_prefix
        self.dir_translate = directive_translate
        if unknown_directive not in ('fail', 'warn', 'ignore'):
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

        shebang = script_data.get('shebang')
        if shebang is not None:
            if not shebang.endswith(b'\n'):
                shebang += b'\n'
            header.append(shebang)

        if self.dir_prefix is not None:
            for name, arg in script_data['directives'].items():
                sentinel = object()
                fmt = self.dir_translate.get(name, sentinel)
                if fmt is sentinel:
                    self._unknown_directive(name)
                    continue
                if fmt is None:
                    continue
                directive = self.dir_prefix + (fmt % arg) + b"\n"
                header.append(directive)

        native = script_data.get('native')
        if native is not None:
            for _, directive in native.values():
                header.append(directive)

        extra = script_data.get('extra')
        if extra is not None:
            header.append(b"\n")
            header.extend(extra)

        return header


    def _unknown_directive(self, name):
        if self.unknown == 'fail':
            raise InvocationError(f"Unknown directive {name!r}")
        if self.unknown == 'warn':
            _logger.warning("Unknown directive %r", name)