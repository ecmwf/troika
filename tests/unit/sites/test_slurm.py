
import os
import stat
import textwrap
import pytest

import troika
from troika.site import get_site
from troika.sites import slurm


@pytest.fixture
def dummy_slurm_conf(tmp_path):
    return {"type": "slurm", "host": "localhost"}


def test_get_site(dummy_slurm_conf):
    global_config = {"sites": {"foo": dummy_slurm_conf}}
    site = get_site(global_config, "foo")
    assert isinstance(site, slurm.SlurmSite)


@pytest.fixture
def dummy_slurm_site(dummy_slurm_conf):
    return slurm.SlurmSite(dummy_slurm_conf)


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


def test_submit_dryrun(dummy_slurm_site, sample_script, tmp_path):
    output = tmp_path / "output.log"
    pid = dummy_slurm_site.submit(sample_script, "user", output, dryrun=True)
    assert pid is None
    assert not output.exists()
