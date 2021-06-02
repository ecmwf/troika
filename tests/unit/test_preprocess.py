
import textwrap
import pytest

import troika.preprocess as pp


@pp.preprocess.register
def drop2(sinput, script, user, output):
    for i, x in enumerate(sinput):
        if i >= 2:
            yield x


@pp.preprocess.register
def delete(sinput, script, user, output):
    for x in sinput:
        if not x.startswith("deleteme"):
            yield x


@pytest.mark.parametrize("sin, sexp, funcs", [
    pytest.param(
        """\
        line1
        line2
        line3
        line4
        """,
        """\
        line1
        line2
        line3
        line4
        """,
        [],
        id="noop"),
    pytest.param(
        """\
        line1
        line2
        line3
        line4
        """,
        """\
        line3
        line4
        """,
        ["drop2"],
        id="drop2"),
    pytest.param(
        """\
        line1
        line2
        deleteme
        line4
        """,
        """\
        line1
        line2
        line4
        """,
        ["delete"],
        id="delete"),
    pytest.param(
        """\
        line1
        deleteme
        line3
        line4
        line5
        """,
        """\
        line3
        line4
        line5
        """,
        ["drop2", "delete"],
        id="drop2, delete"),
    pytest.param(
        """\
        line1
        deleteme
        line3
        line4
        line5
        """,
        """\
        line4
        line5
        """,
        ["delete", "drop2"],
        id="delete, drop2"),
])
def test_hook(sin, sexp, funcs):
    sin = textwrap.dedent(sin)
    sexp = textwrap.dedent(sexp)
    pp.preprocess.instantiate(funcs)
    sout = "".join(pp.preprocess(sin.splitlines(keepends=True), None, None, None))
    assert sout == sexp


@pytest.mark.parametrize("sin, sexp", [
    pytest.param(
        """\
        line1
        line2
        line3
        """,
        """\
        line1
        line2
        line3
        """,
        id="none"),
    pytest.param(
        """\


        line1
        line2
        line3
        """,
        """\
        line1
        line2
        line3
        """,
        id="top"),
    pytest.param(
        """\
        line1

        line2

        line3
        """,
        """\
        line1

        line2

        line3
        """,
        id="middle"),
    pytest.param(
        """\

        line1

        line2

        line3
        """,
        """\
        line1

        line2

        line3
        """,
        id="top+middle"),
])
def test_remove_top_blank_lines(sin, sexp):
    sin = textwrap.dedent(sin).splitlines(keepends=True)
    sexp = textwrap.dedent(sexp).splitlines(keepends=True)
    assert list(pp.remove_top_blank_lines(sin, None, None, None)) == sexp
