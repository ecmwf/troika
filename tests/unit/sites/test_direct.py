
import pytest

import troika
from troika.config import Config
from troika.connections.local import LocalConnection
from troika.site import get_site
from troika.sites import direct


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
    return direct.DirectExecSite(dummy_direct_conf, conn, Config({}))


def test_invalid_script(dummy_direct_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_direct_site.submit(script, "user", "output", dryrun=False)


def test_submit_dryrun(dummy_direct_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    proc = dummy_direct_site.submit(sample_script, "user", output, dryrun=True)
    assert proc is None
    assert not output.exists()


def test_submit(dummy_direct_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    proc = dummy_direct_site.submit(sample_script, "user", output, dryrun=False)
    retcode = proc.wait()
    assert retcode == 0
    assert output.exists()
    assert output.read_text().strip() == "Script called!"
