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
from collections import OrderedDict

from . import InvocationError, RunError


class ParseError(RunError):
    """Exception raised during script parsing"""

    pass


class BaseParser:
    """Base parser class

    Members
    -------
    data: object
        Output data
    """

    data = None

    def __init__(self):
        pass

    def feed(self, line):
        """Feed a line to be processed

        Parameters
        ----------
        line: bytes
            Line to process

        Returns
        -------
        bool
            True if the line can be dropped from the script body
        """
        raise NotImplementedError


class DirectiveParser(BaseParser):
    """Parser that processes a script to extract directives

    Usage
    -----
    Parse a script::

        script = open("myscript", "rb")
        parser = Parser()
        for line in script:
            parser.feed(line)
        data = parser.data

    Members
    -------
    data: collections.OrderedDict[str, bytes]
        Directives that have been parsed
    """

    DIRECTIVE_RE = re.compile(rb"^#\s*troika\s+(.+?)\s*$", re.I)
    KEYVAL_RE = re.compile(rb"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

    def __init__(self, aliases=None):
        super().__init__()
        self.data = OrderedDict()
        self.aliases = aliases if aliases is not None else {}

    def feed(self, line):
        """Process the given line

        See ``BaseParser.feed``
        """
        dm = self.DIRECTIVE_RE.match(line)
        if dm is None:
            return False

        kv = dm.group(1)
        kvm = self.KEYVAL_RE.match(kv)
        if kvm is None:
            raise ParseError(f"Invalid key-value pair: {kv}")

        key, value = kvm.groups()
        key = key.decode("ascii")
        key = self.aliases.get(key, key)
        self.data[key] = value

        return True

    def parse_directive_args(self, args):
        """Process a list of name=value arguments. Returns a dict."""
        data = {}
        for arg in args:
            arg = arg.encode("utf-8")
            m = self.KEYVAL_RE.match(arg)
            if m is None:
                raise InvocationError(f"Invalid key-value pair: {arg!r}")
            key, value = m.groups()
            key = key.decode("ascii")
            key = self.aliases.get(key, key)
            data[key] = value
        return data


class ShebangParser(BaseParser):
    """Parser that extract the 'shebang' line

    The 'shebang' line, if present, must start with '#!' and be the first
    non-blank line fed to the parser.

    Members
    -------
    data: bytes or None
        Shebang line, if found, None otherwise
    """

    def __init__(self):
        super().__init__()
        self.done = False

    def feed(self, line):
        """Process the given line

        See ``BaseParser.feed``
        """
        if self.done:
            return False
        if line.isspace():
            return False
        self.done = True
        if line.startswith(b"#!"):
            self.data = line
            return True
        return False


class MultiParser(BaseParser):
    """Composition of multiple parsers

    A line fed to this parser is fed to each subparser in order, until the
    first True return value.

    Parameters
    ----------
    parsers: [(str, BaseParser)]
        Sub-parsers with labels
    """

    def __init__(self, parsers):
        super().__init__()
        self.parsers = parsers

    def feed(self, line):
        """Process the given line

        See ``BaseParser.feed``
        """
        for _, parser in self.parsers:
            drop = parser.feed(line)
            if drop:
                return True
        return False

    @property
    def data(self):
        return {label: parser.data for label, parser in self.parsers}
