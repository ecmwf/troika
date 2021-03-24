"""Common definitions for tests"""

import doctest
import os
import stat
import textwrap
import types

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


class DocTestItem(pytest.Item):
    class TestFailed(Exception):
        def __init__(self, value):
            self.value = value

    class TestRunner(doctest.DocTestRunner):
        def report_success(self, out, test, example, got):
            pass
        def report_failure(self, out, test, example, got):
            res = []
            super().report_failure((lambda x: res.append(x)), test, example, got)
            raise DocTestItem.TestFailed("".join(res))
        def report_unexpected_exception(self, out, test, example, exc_info):
            res = []
            super().report_unexpected_exception((lambda x: res.append(x)),
                test, example, exc_info)
            raise DocTestItem.TestFailed("".join(res))

    def __init__(self, name, parent, obj, runner):
        super().__init__(name, parent)
        self.test = obj
        self.runner = runner

    def runtest(self):
        self.runner.run(self.test)

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, DocTestItem.TestFailed):
            return str(excinfo.value.value)

    def reportinfo(self):
        fspath, _, _ = super().reportinfo()
        return fspath, 0, self.test.name

    @classmethod
    def from_module_list(cls, parent, lst):
        finder = doctest.DocTestFinder(exclude_empty=True)
        runner = cls.TestRunner()
        for mod in lst:
            if not isinstance(mod, types.ModuleType):
                continue
            for test in finder.find(mod, mod.__name__):
                if not test.examples:
                    continue
                testname = f"doctests[{test.name}]"
                yield cls.from_parent(parent=parent, name=testname,
                    obj=test, runner=runner)


def pytest_pycollect_makeitem(collector, name, obj):
    """Add doctests to the test module
    Circumvents https://github.com/pytest-dev/pytest/issues/1927"""
    if name != '__doctests__':
        return
    return list(DocTestItem.from_module_list(collector, obj))
