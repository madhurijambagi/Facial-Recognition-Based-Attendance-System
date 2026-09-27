import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, _get_bool


def test_get_bool_defaults_when_unset():
    os.environ.pop("SOME_FLAG_TEST", None)
    assert _get_bool("SOME_FLAG_TEST", False) is False
    assert _get_bool("SOME_FLAG_TEST", True) is True


def test_get_bool_parses_truthy_and_falsy_strings():
    for value in ("1", "true", "True", "yes", "on"):
        os.environ["SOME_FLAG_TEST"] = value
        assert _get_bool("SOME_FLAG_TEST") is True

    for value in ("0", "false", "no", "off"):
        os.environ["SOME_FLAG_TEST"] = value
        assert _get_bool("SOME_FLAG_TEST") is False

    del os.environ["SOME_FLAG_TEST"]


def test_config_has_sane_db_defaults():
    for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        os.environ.pop(key, None)

    cfg = Config()
    assert cfg.db_config["host"] == "localhost"
    assert cfg.db_config["database"] == "facial_attendance_mini_project"


def test_config_reads_env_overrides():
    os.environ["DB_NAME"] = "test_db"
    try:
        cfg = Config()
        assert cfg.db_config["database"] == "test_db"
    finally:
        del os.environ["DB_NAME"]


def test_secret_key_defaults_to_none_when_unset():
    os.environ.pop("SECRET_KEY", None)
    cfg = Config()
    assert cfg.SECRET_KEY is None
