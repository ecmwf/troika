
import os
import stat
import textwrap
import pytest

import troika
from troika.site import get_site
from troika.sites import local
from troika.utils import check_status


@pytest.fixture
def dummy_local_conf(tmp_path):
    return {"type": "local"}


def test_get_site(dummy_local_conf):
    global_config = {"sites": {"foo": dummy_local_conf}}
    site = get_site(global_config, "foo")
    assert isinstance(site, local.LocalSite)


@pytest.fixture
def dummy_local_site(dummy_local_conf):
    return local.LocalSite(dummy_local_conf)


def test_invalid_script(dummy_local_site, tmp_path):
    script = tmp_path / "dummy_script.sh"
    with pytest.raises(troika.InvocationError):
        dummy_local_site.submit(script, "user", "output", dryrun=False)


def test_preprocess(dummy_local_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pp_script = dummy_local_site.preprocess(sample_script, "user", output)
    assert pp_script == sample_script


def test_submit_dryrun(dummy_local_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pid = dummy_local_site.submit(sample_script, "user", output, dryrun=True)
    assert pid is None
    assert not output.exists()


def test_submit(dummy_local_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pid = dummy_local_site.submit(sample_script, "user", output, dryrun=False)
    _, sts = os.waitpid(pid, 0)
    assert check_status(sts) == 0
    assert output.exists()
    assert output.read_text().strip() == "Script called!"
