
import os
import stat
import textwrap
import pytest

import troika
from troika.site import get_site
from troika.sites import ssh


@pytest.fixture
def dummy_ssh_conf(tmp_path):
    return {"type": "ssh", "host": "localhost"}


def test_get_site(dummy_ssh_conf):
    global_config = {"sites": {"foo": dummy_ssh_conf}}
    site = get_site(global_config, "foo")
    assert isinstance(site, ssh.SSHSite)


@pytest.fixture
def dummy_ssh_site(dummy_ssh_conf):
    return ssh.SSHSite(dummy_ssh_conf)


def test_invalid_script(dummy_ssh_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_ssh_site.submit(script, "user", "output", dryrun=False)


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


def test_preprocess(dummy_ssh_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pp_script = dummy_ssh_site.preprocess(sample_script, "user", output)
    assert pp_script == sample_script


def test_submit_dryrun(dummy_ssh_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pid = dummy_ssh_site.submit(sample_script, "user", output, dryrun=True)
    assert pid is None
    assert not output.exists()
