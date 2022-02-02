
import pytest

import troika
from troika.config import Config
from troika.site import get_site
from troika.sites.base import Site
import troika.sites.base


class DummySite(Site):
    pass


@pytest.fixture
def dummy_sites(monkeypatch):
    fake_sites = {"dummy": DummySite}
    def fake_discover(package, plugins, base, attrname=""):
        return fake_sites
    monkeypatch.setattr("troika.site.discover", fake_discover)


def test_get_exist(dummy_sites):
    cfg = Config({"sites": {"foo": {"type": "dummy", "connection": "local"}}})
    site = get_site(cfg, "foo", "user", [])
    assert isinstance(site, DummySite)


def test_get_nonexistent(dummy_sites):
    cfg = Config({"sites": {"foo": {"type": "dummy", "connection": "local"}}})
    with pytest.raises(troika.InvocationError):
        get_site(cfg, "unknown", "user", [])


def test_get_nosites(dummy_sites):
    cfg = Config({})
    with pytest.raises(troika.ConfigurationError):
        get_site(cfg, "bar", "user", [])


def test_get_notype(dummy_sites):
    cfg = Config({"sites": {"bar": {"connection": "local"}}})
    with pytest.raises(troika.ConfigurationError):
        get_site(cfg, "bar", "user", [])


def test_get_wrongtype(dummy_sites):
    cfg = Config({"sites": {"bar": {"type": "nonexistent", "connection": "local"}}})
    with pytest.raises(troika.ConfigurationError):
        get_site(cfg, "bar", "user", [])


def test_get_noconn(dummy_sites):
    cfg = Config({"sites": {"bar": {"type": "dummy"}}})
    with pytest.raises(troika.ConfigurationError):
        get_site(cfg, "bar", "user", [])


def test_get_base():
    cfg = Config({"sites": {"what": {"type": "base", "connection": "local"}}})
    with pytest.raises(troika.ConfigurationError):
        get_site(cfg, "what", "user", [])
