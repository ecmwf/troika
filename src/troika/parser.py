"""Script parsing logic

Troika directives are of the form::

    # troika key=value

To be recognised, a line **must** start with the # sign, optionally followed by
white space, the string "troika" (case-insensitive), at least one white space
character, and a key-value pair. Valid keys consist only of letters, numbers
and underscores, and do not start with a number. Whitespace is removed around
the equals sign and at the end the value.
"""

import re

from . import RunError


class ParseError(RunError):
    """Exception raised during script parsing"""
    def __init__(self, msg, fname=None, line=None):
        full_msg = ""
        if fname is not None:
            full_msg += f"in {fname}, "
        if line is not None:
            full_msg += f"line {line}, "
        full_msg += msg
        super().__init__(full_msg)
        self.fname = fname
        self.line = line


class Parser:
    """Simple parser that processes a script to extract directives

    Usage
    -----
    Parse a script::

        script = open("myscript", "rb")
        parser = Parser(script.name)
        for line in script:
            parser.feed(line)
        data = parser.data

    Parameters
    ----------
    scriptname: str or None
        Name of the script, for error reporting (omitted if None)
    """

    DIRECTIVE_RE = re.compile(rb"^#\s*troika\s+(.+?)\s*$", re.I)
    KEYVAL_RE = re.compile(rb"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

    def __init__(self, scriptname=None):
        self.scriptname = scriptname
        self.line = 0
        self.data = {}

    def feed(self, line):
        """Process the given line

        Parameters
        ----------
        line: bytes
            Line to process

        Returns
        -------
        bool
            True if a valid directive has been found
        """
        self.line += 1

        dm = self.DIRECTIVE_RE.match(line)
        if dm is None:
            return False

        kv = dm.group(1)
        kvm = self.KEYVAL_RE.match(kv)
        if kvm is None:
            raise ParseError(f"Invalid key-value pair: {kv}", self.scriptname, self.line)

        key, value = kvm.groups()
        self.data[key.decode('ascii')] = value

        return True


def parse_script(script):
    """Parse the given script

    Parameters
    ----------
    script: file-like
        Input script

    Returns
    -------
    dict
        Key-value pairs defined in the script
    """

    sname = getattr(script, "name", None)
    parser = Parser(sname)

    for line in script:
        parser.feed(line)

    return parser.data
