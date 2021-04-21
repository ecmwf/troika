
import textwrap
import pytest

import troika.preprocess as pp


def make_pp_object(pp_funcs):
    class Preprocess(pp.PreprocessMixin):
        preprocessors = pp_funcs
    return Preprocess()


def drop2(script, user, output, sinput):
    for i, x in enumerate(sinput):
        if i >= 2:
            yield x

def delete(script, user, output, sinput):
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
        [drop2],
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
        [delete],
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
        [drop2, delete],
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
        [delete, drop2],
        id="delete, drop2"),
])
def test_mixin(sin, sexp, funcs, tmp_path):
    script = tmp_path / "script.sh"
    orig_script = tmp_path / "script.sh.orig"
    output = tmp_path / "output.log"
    sin = textwrap.dedent(sin)
    script.write_text(sin)
    sexp = textwrap.dedent(sexp)
    proc = make_pp_object(funcs)
    pp_script = proc.preprocess(script, "user", output)
    assert pp_script == script
    assert pp_script.read_text() == sexp
    assert orig_script.exists()
    assert orig_script.read_text() == sin


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
    assert list(pp.remove_top_blank_lines(None, None, None, sin)) == sexp