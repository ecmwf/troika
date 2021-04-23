
import os
import stat
import textwrap
import pytest

import troika
from troika.config import Config
from troika.connection import LocalConnection
from troika.site import get_site
from troika.sites import direct
from troika.utils import check_status


@pytest.fixture
def dummy_direct_conf(tmp_path):
    return {"type": "direct", "connection": "local"}


def test_get_site(dummy_direct_conf):
    global_config = Config({"sites": {"foo": dummy_direct_conf}})
    site = get_site(global_config, "foo", "user")
    assert isinstance(site, direct.DirectExecSite)


@pytest.fixture
def dummy_direct_site(dummy_direct_conf):
    conn = LocalConnection(dummy_direct_conf, "user")
    return direct.DirectExecSite(dummy_direct_conf, conn)


def test_invalid_script(dummy_direct_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_direct_site.submit(script, "user", "output", dryrun=False)


def test_preprocess(dummy_direct_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pp_script = dummy_direct_site.preprocess(sample_script, "user", output)
    assert pp_script == sample_script


def test_submit_dryrun(dummy_direct_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pid = dummy_direct_site.submit(sample_script, "user", output, dryrun=True)
    assert pid is None
    assert not output.exists()


def test_submit(dummy_direct_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pid = dummy_direct_site.submit(sample_script, "user", output, dryrun=False)
    _, sts = os.waitpid(pid, 0)
    assert check_status(sts) == 0
    assert output.exists()
    assert output.read_text().strip() == "Script called!"
