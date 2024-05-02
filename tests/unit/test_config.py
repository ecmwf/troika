import pytest

from troika import ConfigurationError, InvocationError
from troika.config import Config, get_config


def test_get_site_nosites():
    cfg = Config({})
    with pytest.raises(ConfigurationError):
        cfg.get_site_config("foo")


def test_get_site_exist():
    cfg = Config({"sites": {"foo": {}}})
    site_cfg = cfg.get_site_config("foo")
    assert isinstance(site_cfg, dict)


def test_get_site_nonexistent():
    cfg = Config({"sites": {"foo": {}}})
    with pytest.raises(KeyError):
        cfg.get_site_config("bar")


def test_arg_valid(tmp_path):
    cfile = tmp_path / "config.yaml"
    cfile.write_text("---\nfoo: bar")
    cfg = get_config(cfile)
    assert isinstance(cfg, Config)
    assert cfg.get("foo") == "bar"


def test_arg_valid_fileobj(tmp_path):
    cfile = tmp_path / "config.yaml"
    cfile.write_text("---\nfoo: bar")
    cfg = get_config(cfile.open())
    assert isinstance(cfg, Config)
    assert cfg.get("foo") == "bar"


def test_arg_nonexistent(tmp_path):
    cfile = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError):
        get_config(cfile)


def test_arg_invalid(tmp_path):
    cfile = tmp_path / "invalid.yaml"
    cfile.write_text("---\nfoo: {")
    with pytest.raises(ConfigurationError):
        get_config(cfile)


def test_env_valid(tmp_path, monkeypatch):
    cfile = tmp_path / "config.yaml"
    cfile.write_text("---\nfoo: spam")
    monkeypatch.setenv("TROIKA_CONFIG_FILE", str(cfile.resolve()))
    cfg = get_config()
    assert isinstance(cfg, Config)
    assert cfg.get("foo") == "spam"


def test_env_nonexistent(tmp_path, monkeypatch):
    cfile = tmp_path / "nonexistent.yaml"
    monkeypatch.setenv("TROIKA_CONFIG_FILE", str(cfile.resolve()))
    with pytest.raises(FileNotFoundError):
        get_config()


def test_env_invalid(tmp_path, monkeypatch):
    cfile = tmp_path / "invalid.yaml"
    cfile.write_text("---\nfoo: {")
    monkeypatch.setenv("TROIKA_CONFIG_FILE", str(cfile.resolve()))
    with pytest.raises(ConfigurationError):
        get_config()


def test_arg_valid_env_valid(tmp_path, monkeypatch):
    cfile = tmp_path / "config.yaml"
    cfile.write_text("---\nfoo: bar")
    cfile2 = tmp_path / "config2.yaml"
    cfile2.write_text("---\nfoo: spam")
    monkeypatch.setenv("TROIKA_CONFIG_FILE", str(cfile2.resolve()))
    cfg = get_config(cfile)
    assert cfg.get("foo") == "bar"


def test_arg_nonexistent_env_valid(tmp_path, monkeypatch):
    cfile = tmp_path / "nonexistent.yaml"
    cfile2 = tmp_path / "config.yaml"
    cfile2.write_text("---\nfoo: spam")
    monkeypatch.setenv("TROIKA_CONFIG_FILE", str(cfile2.resolve()))
    with pytest.raises(FileNotFoundError):
        get_config(cfile)


def test_arg_invalid_env_valid(tmp_path, monkeypatch):
    cfile = tmp_path / "invalid.yaml"
    cfile.write_text("---\nfoo: {")
    cfile2 = tmp_path / "config.yaml"
    cfile2.write_text("---\nfoo: spam")
    monkeypatch.setenv("TROIKA_CONFIG_FILE", str(cfile2.resolve()))
    with pytest.raises(ConfigurationError):
        get_config(cfile)


def test_noconf():
    with pytest.raises(InvocationError):
        get_config()
