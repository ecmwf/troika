
import argparse
import logging
import os
import textwrap
import pytest

import troika.cli


@pytest.fixture
def config_file(tmp_path):
    cfg_path = tmp_path / "basic_config.yml"
    cfg_path.write_text(textwrap.dedent("""\
        ---
        sites:
            localhost:
                type: direct
                connection: local
        """))
    return cfg_path


def test_submit_dryrun(tmp_path, config_file, sample_script):
    output_file = tmp_path / "output.log"
    args = ['-n', '-c', str(config_file.resolve()), 'submit',
            '-u', 'user', '-o', str(output_file.resolve()),
            'localhost', str(sample_script.resolve())]
    sts = troika.cli.main(args=args)
    assert sts == 0
    assert not output_file.exists()


def test_submit(tmp_path, config_file, sample_script, caplog):
    output_file = tmp_path / "output.log"
    args = ['-c', str(config_file.resolve()), 'submit',
            '-u', 'user', '-o', str(output_file.resolve()),
            'localhost', str(sample_script.resolve())]
    with caplog.at_level(logging.DEBUG):
        sts = troika.cli.main(args=args)
    assert sts == 0
    pid_rec = [rec for rec in caplog.records
               if rec.levelname == 'DEBUG'
               and rec.msg == "Child PID: %d"]
    assert len(pid_rec) == 1
    pid = pid_rec[0].args[0]
    _, sts = os.waitpid(pid, 0)
    assert os.WIFEXITED(sts) and os.WEXITSTATUS(sts) == 0
    assert output_file.exists()
    assert output_file.read_text().strip() == "Script called!"
