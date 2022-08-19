"""Common definitions for tests"""

import stat
import textwrap

import pytest


@pytest.fixture
def sample_script(tmp_path):
    """Trivial sample script fixture"""
    script_path = tmp_path / "sample_script.sh"
    script_path.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        echo "Script called!"
        """))
    script_path.chmod(script_path.stat().st_mode
                      | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script_path