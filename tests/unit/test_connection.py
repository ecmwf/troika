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

    def fake_get_entrypoint(group, name):
        try:
            return fake_connections[name]
        except KeyError:
            raise ValueError(name)

    monkeypatch.setattr("troika.connection.get_entrypoint", fake_get_entrypoint)


def test_get_exist(dummy_connections):
    cfg = {}
    conn = connection.get_connection("dummy", cfg, "user")
    assert isinstance(conn, DummyConnection)


def test_get_nonexistent(dummy_connections):
    cfg = {}
    with pytest.raises(troika.ConfigurationError):
        connection.get_connection("unknown", cfg, "user")


def test_get_local():
    cfg = {}
    conn = connection.get_connection("local", cfg, "user")
    assert isinstance(conn, LocalConnection)


def test_get_ssh():
    cfg = {"host": "localhost"}
    conn = connection.get_connection("ssh", cfg, "user")
    assert isinstance(conn, SSHConnection)


def test_local_islocal():
    cfg = {}
    conn = connection.get_connection("local", cfg, "user")
    assert conn.is_local()


def test_ssh_islocal():
    cfg = {"host": "localhost"}
    conn = connection.get_connection("ssh", cfg, "user")
    assert not conn.is_local()


def test_local_parent():
    cfg = {}
    conn = connection.get_connection("local", cfg, "user")
    assert conn.get_parent() == conn


def test_ssh_parent():
    cfg = {"host": "localhost"}
    conn = connection.get_connection("ssh", cfg, "user")
    assert isinstance(conn.get_parent(), LocalConnection)
