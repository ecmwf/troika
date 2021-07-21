
import stat
import textwrap
import pytest

import troika
from troika.config import Config
from troika.connections.local import LocalConnection
from troika.hook import setup_hooks
from troika.site import get_site
from troika.sites import slurm


__doctests__ = [slurm]


@pytest.fixture
def dummy_slurm_conf(tmp_path):
    return {
        "type": "slurm",
        "connection": "local",
        "preprocess": ["remove_top_blank_lines", "slurm_add_output", "slurm_bubble"]
    }


def test_get_site(dummy_slurm_conf):
    global_config = Config({"sites": {"foo": dummy_slurm_conf}})
    site = get_site(global_config, "foo", "user")
    assert isinstance(site, slurm.SlurmSite)


@pytest.fixture
def dummy_slurm_site(dummy_slurm_conf):
    conn = LocalConnection(dummy_slurm_conf, "user")
    return slurm.SlurmSite(dummy_slurm_conf, conn, Config({}))


def test_invalid_script(dummy_slurm_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_slurm_site.submit(script, "user", "output", dryrun=False)


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
        #SBATCH --output=@OUTPUT@
        echo "Hello, World!"
        """,
        id="add_output"),
    pytest.param(
        """\n\n
        #!/usr/bin/env bash
        #SBATCH -J hello

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        echo "Hello, World!"
        """,
        id="blanks"),
    pytest.param(
        """\
        #SBATCH -n 1

        set +x

        #SBATCH -J hello

        echo "Hello, World!"
        """,
        """\
        #SBATCH -n 1
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        set +x


        echo "Hello, World!"
        """,
        id="bubble"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #SBATCH -n 1

        set +x

        #SBATCH -J hello

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #SBATCH -n 1
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        set +x


        echo "Hello, World!"
        """,
        id="bubble_shebang"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH -e foo

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_error"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --error=foo

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_error2"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH -o foo

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_output"),
    pytest.param(
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --output=foo

        echo "Hello, World!"
        """,
        """\
        #!/usr/bin/env bash
        #SBATCH -J hello
        #SBATCH --output=@OUTPUT@

        echo "Hello, World!"
        """,
        id="drop_output2"),
])
def test_preprocess(sin, sexp, dummy_slurm_conf, dummy_slurm_site, tmp_path):
    script = tmp_path / "script.sh"
    orig_script = tmp_path / "script.sh.orig"
    output = tmp_path / "output.log"
    sin = textwrap.dedent(sin)
    script.write_text(sin)
    sexp = textwrap.dedent(sexp).replace("@OUTPUT@", str(output.resolve()))
    global_config = Config({"sites": {"foo": dummy_slurm_conf}})
    setup_hooks(global_config, "foo")
    pp_script = dummy_slurm_site.preprocess(script, "user", output)
    assert pp_script == script
    assert pp_script.read_text() == sexp
    assert orig_script.exists()
    assert orig_script.read_text() == sin


def test_submit_dryrun(dummy_slurm_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    proc = dummy_slurm_site.submit(sample_script, "user", output, dryrun=True)
    assert proc is None
    assert not output.exists()
