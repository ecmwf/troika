
import pytest
import textwrap

from troika.parser import DirectiveParser, ParseError


@pytest.mark.parametrize("script, expect", [
    pytest.param(
        """\
        #!/usr/bin/env bash

        # Hello
        text="Hello, World!"
        echo $text
        """,
        {},
        id="nodir"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #TROIKA foo=bar

        # Hello
        text="Hello, World!"
        echo $text
        """,
        {"foo": b"bar"},
        id="onedir"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #TROIKA foo=bar
        #TROIKA empty=

        # Hello
        #TROIKA name=unknown name
        text="Hello, World!"
        echo $text
        """,
        {"foo": b"bar", "empty": b"", "name": b"unknown name"},
        id="multi"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #  TROIKA spaces = yes 

        # Hello
        # TROIKA name=unknown name
        text="Hello, World!"
        echo $text
        """,
        {"spaces": b"yes", "name": b"unknown name"},
        id="spaces"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #TROIKA foo=bar
        #TROIKA spam=eggs
        #TROIKA spam=beans

        # Hello
        text="Hello, World!"
        echo $text
        """,
        {"foo": b"bar", "spam": b"beans"},
        id="duplicate"),
])
def test_parse(script, expect):
    lines = textwrap.dedent(script).encode('ascii').splitlines()
    parser = DirectiveParser()
    for line in lines:
        parser.feed(line)
    params = parser.data
    assert params == expect


@pytest.mark.parametrize("script, errline", [
    pytest.param(
        """\
        #!/usr/bin/env bash
        #TROIKA help

        # Hello
        text="Hello, World!"
        echo $text
        """,
        2,
        id="noval"),

    pytest.param(
        """\
        #!/usr/bin/env bash
        #TROIKA foo=bar
        #TROIKA 123=456

        # Hello
        text="Hello, World!"
        echo $text
        """,
        3,
        id="badkey"),
])
def test_parse_error(script, errline):
    lines = textwrap.dedent(script).encode('ascii').splitlines()
    parser = DirectiveParser()
    with pytest.raises(ParseError,
            match="Invalid key-value pair:.*"):
        for lno, line in enumerate(lines, start=1):
            parser.feed(line)
    assert lno == errline

