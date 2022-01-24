"""Script header generation logic"""

import logging

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
    """


    def __init__(self, directive_prefix, directive_translate):
        self.dir_prefix = directive_prefix
        self.dir_translate = directive_translate

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

        shebang = script_data.get('shebang')
        if shebang is not None:
            header.append(shebang)

        if self.dir_prefix is not None:
            for name, arg in script_data['directives'].items():
                fmt = self.dir_translate.get(name)
                if fmt is None:
                    continue
                directive = self.dir_prefix + (fmt % arg) + b"\n"
                header.append(directive)

        native = script_data.get('native')
        if native is not None:
            for _, directive in native.values():
                header.append(directive)

        return header
