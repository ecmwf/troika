import signal

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


@pytest.mark.parametrize(
    "seq",
    [
        pytest.param(None, id="invalid_type"),
        pytest.param([2, 15, 9], id="not_tuples"),
        pytest.param([(0, 2), (5, -3), (10, 9)], id="invalid_number"),
        pytest.param([(0, "XXXINVALID"), (5, 15), (10, 9)], id="invalid_name"),
    ],
)
def test_invalid_killseq(seq, dummy_direct_conf):
    cfg = dummy_direct_conf.copy()
    cfg["kill_sequence"] = seq
    conn = LocalConnection(dummy_direct_conf, "user")
    with pytest.raises(troika.ConfigurationError, match="Invalid kill sequence"):
        direct.DirectExecSite(cfg, conn, Config({}))


def test_valid_killseq(dummy_direct_conf):
    seq = [(0, 2), (5, "TERM"), (10, "SIGKILL")]
    exp = [(0, signal.SIGINT), (5, signal.SIGTERM), (10, signal.SIGKILL)]
    cfg = dummy_direct_conf.copy()
    cfg["kill_sequence"] = seq
    conn = LocalConnection(dummy_direct_conf, "user")
    site = direct.DirectExecSite(cfg, conn, Config({}))
    assert site._kill_sequence == exp


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
