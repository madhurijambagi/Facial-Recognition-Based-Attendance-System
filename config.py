"""Centralized application configuration, loaded from environment variables.

Copy `.env.example` to `.env` and fill in real values before running the
app. `.env` is already excluded via .gitignore — never commit real
credentials.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional at runtime; if it's not installed,
    # environment variables must be set another way (shell export,
    # Docker `environment:`, systemd unit, etc.)
    pass


def _get_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Reads env vars at instantiation time (not import time), so tests can
    set os.environ and construct a fresh Config() to see the change."""

    def __init__(self):
        self.SECRET_KEY = os.environ.get("SECRET_KEY")
        self.DEBUG      = _get_bool("FLASK_DEBUG", False)

        self.DB_HOST     = os.environ.get("DB_HOST", "localhost")
        self.DB_USER     = os.environ.get("DB_USER", "root")
        self.DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
        self.DB_NAME     = os.environ.get("DB_NAME", "facial_attendance_mini_project")

    @property
    def db_config(self):
        return {
            "host":     self.DB_HOST,
            "user":     self.DB_USER,
            "password": self.DB_PASSWORD,
            "database": self.DB_NAME,
        }


config = Config()
