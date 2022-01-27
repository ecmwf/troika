
import stat
import textwrap
import pytest

import troika
from troika.config import Config
from troika.connections.local import LocalConnection
from troika.hook import setup_hooks
from troika.site import get_site
from troika.sites import pbs


__doctests__ = [pbs]


@pytest.fixture
def dummy_pbs_conf(tmp_path):
    return {
        "type": "pbs",
        "connection": "local",
        "preprocess": ["remove_top_blank_lines", "pbs_add_output", "pbs_bubble"]
    }


def test_get_site(dummy_pbs_conf):
    global_config = Config({"sites": {"foo": dummy_pbs_conf}})
    site = get_site(global_config, "foo", "user")
    assert isinstance(site, pbs.PBSSite)


@pytest.fixture
def dummy_pbs_site(dummy_pbs_conf):
    conn = LocalConnection(dummy_pbs_conf, "user")
    return pbs.PBSSite(dummy_pbs_conf, conn, Config({}))


def test_invalid_script(dummy_pbs_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_pbs_site.submit(script, "user", "output", dryrun=False)


@pytest.fixture
def sample_script(tmp_path):
    script_path = tmp_path / "script.sh"
    script_path.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        echo "Script called!"
        """))
    script_path.chmod(script_path.stat().st_mode
                      | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script_path


@pytest.mark.parametrize("sin, sexp", [
    pytest.param(
        """\
        #!/usr/bin/env bash
        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -j oe
        #PBS -o @OUTPUT@
        echo "Hello, World!"
        """,
        id="add_output"),
    pytest.param(
        """\n\n
        #!/usr/bin/env bash
        #PBS -N hello

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        echo "Hello, World!"
        """,
        id="blanks"),
    pytest.param(
        """\
        #PBS -q test

        set +x

        #PBS -N hello

        echo "Hello, World!"
        """,
        """\
        #PBS -q test
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        set +x


        echo "Hello, World!"
        """,
        id="bubble"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #PBS -q test

        set +x

        #PBS -N hello

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -q test
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        set +x


        echo "Hello, World!"
        """,
        id="bubble_shebang"),
    pytest.param(
        """\
        #PBS -q test

        #!/usr/bin/env bash

        set +x

        #PBS -N hello

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -q test
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@


        set +x


        echo "Hello, World!"
        """,
        id="bubble_shebang_blank"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -e foo

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_error"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j n
        #PBS -e foo
        #PBS -o bar

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_join"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -o foo

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_output"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #PBS -N hello

        echo "\xfc\xaa"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        echo "\xfc\xaa"
        """,
        id="invalid_utf8"),
])
def test_preprocess(sin, sexp, dummy_pbs_conf, dummy_pbs_site, tmp_path):
    script = tmp_path / "script.sh"
    orig_script = tmp_path / "script.sh.orig"
    output = tmp_path / "output.log"
    sin = textwrap.dedent(sin)
    script.write_text(sin)
    sexp = textwrap.dedent(sexp).replace("@OUTPUT@", str(output.resolve()))
    global_config = Config({"sites": {"foo": dummy_pbs_conf}})
    setup_hooks(global_config, "foo")
    pp_script = dummy_pbs_site.preprocess(script, "user", output)
    assert pp_script == script
    assert pp_script.read_text() == sexp
    assert orig_script.exists()
    assert orig_script.read_text() == sin


@pytest.mark.parametrize("sin, sexp, garbage", [
    pytest.param(
        """\
        #!/usr/bin/env bash
        #PBS -N hello

        echo "@GARBAGE@"
        """,
        """\
        #!/usr/bin/env bash
        #PBS -N hello
        #PBS -j oe
        #PBS -o @OUTPUT@

        echo "@GARBAGE@"
        """,
        b"\xfc\xaa",
        id="invalid_utf8"),
])
def test_preprocess_bin(sin, sexp, garbage, dummy_pbs_conf, dummy_pbs_site, tmp_path):
    script = tmp_path / "script.sh"
    orig_script = tmp_path / "script.sh.orig"
    output = tmp_path / "output.log"
    sin = textwrap.dedent(sin).encode('utf-8').replace(b"@GARBAGE@", garbage)
    script.write_bytes(sin)
    sexp = textwrap.dedent(sexp).replace("@OUTPUT@", str(output.resolve()))
    sexp = sexp.encode('utf-8').replace(b"@GARBAGE@", garbage)
    global_config = Config({"sites": {"foo": dummy_pbs_conf}})
    setup_hooks(global_config, "foo")
    pp_script = dummy_pbs_site.preprocess(script, "user", output)
    assert pp_script == script
    assert pp_script.read_bytes() == sexp
    assert orig_script.exists()
    assert orig_script.read_bytes() == sin


def test_submit_dryrun(dummy_pbs_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    proc = dummy_pbs_site.submit(sample_script, "user", output, dryrun=True)
    assert proc is None
    assert not output.exists()


@pytest.mark.parametrize("path_type", [
    pytest.param((lambda x: x), id="path"),
    pytest.param(str, id="str"),
    pytest.param(bytes, id="bytes"),
])
def test_output_path_type(path_type, dummy_pbs_conf, dummy_pbs_site, sample_script, tmp_path):
    output = path_type(tmp_path / "output.log")
    global_config = Config({"sites": {"foo": dummy_pbs_conf}})
    setup_hooks(global_config, "foo")
    pp_script = dummy_pbs_site.preprocess(sample_script, "user", output)
    assert pp_script == sample_script
