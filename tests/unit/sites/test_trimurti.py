
import stat
import textwrap
import pytest

import troika
from troika.site import get_site
from troika.sites import trimurti


@pytest.fixture
def dummy_trimurti_conf(tmp_path):
    output_path = tmp_path / "trimurti_output.log"
    trimurti_path = tmp_path / "fake_trimurti"
    trimurti_path.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        while [[ $# > 0 ]] ; do
            echo "$1" >>{output_path!s}
            shift
        done
        """))
    trimurti_path.chmod(trimurti_path.stat().st_mode
                        | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"type": "trimurti", "host": "dummy", "trimurti_path": trimurti_path}


def test_get_site(dummy_trimurti_conf):
    global_config = {"sites": {"foo": dummy_trimurti_conf}}
    site = get_site(global_config, "foo")
    assert isinstance(site, trimurti.TrimurtiSite)
    assert site._host == "dummy"
    assert dummy_trimurti_conf["trimurti_path"].samefile(site._trimurti_path)


def test_invalid_trimurti_path(tmp_path):
    trimurti_path = tmp_path / "nonexistent"
    conf = {"type": "trimurti", "host": "dummy", "trimurti_path": trimurti_path}
    with pytest.raises(troika.ConfigurationError):
        site = trimurti.TrimurtiSite(conf)


@pytest.fixture
def dummy_trimurti_site(dummy_trimurti_conf):
    return trimurti.TrimurtiSite(dummy_trimurti_conf)


def test_invalid_script(dummy_trimurti_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_trimurti_site.submit(script, "user", "output", dryrun=False)


def test_preprocess(dummy_trimurti_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pp_script = dummy_trimurti_site.preprocess(sample_script, "user", output)
    assert pp_script == sample_script


def test_submit_dryrun(dummy_trimurti_site, tmp_path):
    logfile_path = tmp_path / "trimurti_output.log"
    script = tmp_path / "dummy_script.sh"
    script.touch()
    dummy_trimurti_site.submit(script, "user", "output", dryrun=True)
    assert not logfile_path.exists()


def test_submit(dummy_trimurti_site, tmp_path):
    logfile_path = tmp_path / "trimurti_output.log"
    script = tmp_path / "dummy_script.sh"
    script.touch()
    dummy_trimurti_site.submit(script, "user", "output", dryrun=False)
    assert logfile_path.exists()
    log = logfile_path.read_text().splitlines()
    assert "user" == log[0].rstrip()
    assert "dummy" == log[1].rstrip()
    assert script.samefile(log[2].rstrip())
    assert "output" == log[3].rstrip()
