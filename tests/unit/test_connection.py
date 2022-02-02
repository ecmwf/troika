
import pytest

import troika
from troika import connection
from troika.connections.base import Connection
from troika.connections.local import LocalConnection
from troika.connections.ssh import SSHConnection


class DummyConnection(Connection):
    pass


@pytest.fixture
def dummy_connections(monkeypatch):
    fake_connections = {"dummy": DummyConnection}
    def fake_discover(package, plugins, base, attrname=""):
        return fake_connections
    monkeypatch.setattr("troika.connection.discover", fake_discover)


def test_get_exist(dummy_connections):
    cfg = {}
    conn = connection.get_connection("dummy", cfg, "user", [])
    assert isinstance(conn, DummyConnection)


def test_get_nonexistent(dummy_connections):
    cfg = {}
    with pytest.raises(troika.ConfigurationError):
        connection.get_connection("unknown", cfg, "user", [])


def test_get_local():
    cfg = {}
    conn = connection.get_connection("local", cfg, "user", [])
    assert isinstance(conn, LocalConnection)


def test_get_ssh():
    cfg = {"host": "localhost"}
    conn = connection.get_connection("ssh", cfg, "user", [])
    assert isinstance(conn, SSHConnection)
