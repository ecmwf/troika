
import argparse
import pytest

import troika.cli
from troika.config import Config
from troika.sites.base import Site


@pytest.fixture
def dummy_site():
    class DummySite(Site):
        def __init__(self, config, connection):
            self.preprocess_called = False
            self.submit_called = False
            self.monitor_called = False
            self.kill_called = False
        def preprocess(self, script, user, output):
            self.preprocess_called = True
            return script
        def submit(self, script, user, output, dryrun=False):
            self.submit_called = True
        def monitor(self, dryrun=False):
            self.monitor_called = True
        def kill(self, script, user, jid=None, dryrun=False):
            self.kill_called = True
    dummy = DummySite({}, None)
    return dummy


@pytest.fixture
def dummy_actions(monkeypatch, dummy_site):
    monkeypatch.setattr(troika.cli, "get_config", lambda config: Config({}))
    monkeypatch.setattr(troika.cli, "get_site", lambda config, site, user: dummy_site)
    monkeypatch.setattr(troika.cli.hook, "setup_hooks", lambda config, site: None)

    def make_dummy_action():
        def dummy_action(site, args):
            dummy_action.called = True
            dummy_action.site = site
            dummy_action.args = args
            return 0
        dummy_action.called = False
        dummy_action.site = None
        dummy_action.args = None
        return dummy_action

    actions = {}
    for act in ["submit", "monitor", "kill"]:
        actions[act] = make_dummy_action()
        monkeypatch.setattr(troika.cli, act, actions[act])

    return actions


def test_main_submit(dummy_actions, dummy_site):
    args = ["-l", "/dev/null", "submit", "-u", "user", "-o", "output", "site", "script"]
    sts = troika.cli.main(args=args)
    act_args = dummy_actions["submit"].args
    assert sts == 0
    assert not dummy_actions["monitor"].called
    assert not dummy_actions["kill"].called
    assert dummy_actions["submit"].called
    assert dummy_actions["submit"].site is dummy_site
    assert act_args.user == "user"
    assert act_args.output == "output"
    assert act_args.site == "site"
    assert act_args.script == "script"


def test_main_monitor(dummy_actions, dummy_site):
    args = ["-l", "/dev/null", "monitor", "site"]
    sts = troika.cli.main(args=args)
    act_args = dummy_actions["monitor"].args
    assert sts == 0
    assert not dummy_actions["submit"].called
    assert not dummy_actions["kill"].called
    assert dummy_actions["monitor"].called
    assert dummy_actions["monitor"].site is dummy_site
    assert act_args.site == "site"


def test_main_kill(dummy_actions, dummy_site):
    args = ["-l", "/dev/null", "kill", "-u", "user", "site", "script"]
    sts = troika.cli.main(args=args)
    act_args = dummy_actions["kill"].args
    assert sts == 0
    assert not dummy_actions["submit"].called
    assert not dummy_actions["monitor"].called
    assert dummy_actions["kill"].called
    assert dummy_actions["kill"].site is dummy_site
    assert act_args.site == "site"


def test_submit(dummy_site):
    args = argparse.Namespace(site="dummy", script="script", user="user",
        output="output", dryrun=True)
    sts = troika.cli.submit(dummy_site, args)
    assert sts == 0
    assert dummy_site.preprocess_called
    assert dummy_site.submit_called


@pytest.mark.xfail(reason="Not implemented")
def test_monitor(dummy_site):
    args = argparse.Namespace(site="dummy", dryrun=True)
    sts = troika.cli.monitor(dummy_site, args)
    assert sts == 0
    assert dummy_site.monitor_called


def test_kill(dummy_site):
    args = argparse.Namespace(site="dummy", script="script", user="user",
        jobid="1234", dryrun=True)
    sts = troika.cli.kill(dummy_site, args)
    assert sts == 0
    assert dummy_site.kill_called
