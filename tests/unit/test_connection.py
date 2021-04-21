
import pytest

import troika
from troika import connection


class DummyConnection(connection.Connection):
    pass


@pytest.fixture
def dummy_connections(monkeypatch):
    fake_connections = {"dummy": DummyConnection}
    monkeypatch.setattr("troika.connection._CONNECTIONS", fake_connections)


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
    assert isinstance(conn, connection.LocalConnection)


def test_get_ssh():
    cfg = {"host": "localhost"}
    conn = connection.get_connection("ssh", cfg, "user")
    assert isinstance(conn, connection.SSHConnection)
