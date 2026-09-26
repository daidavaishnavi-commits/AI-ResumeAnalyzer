"""Application configuration.

The configuration is chosen explicitly: an unknown `FLASK_CONFIG` is an error
and an unset one means production, so a typo can never silently start the app
with debug settings.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_UPLOAD_RETENTION_SECONDS = 15 * 60
DEV_SECRET_KEY = "development-only-insecure-key"


class ConfigurationError(RuntimeError):
    """Raised when the app is asked to start with an unsafe configuration."""


class Config:
    # No fallback: the real key comes from the SECRET_KEY environment variable.
    SECRET_KEY: str | None = None
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(INSTANCE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES
    ALLOWED_EXTENSIONS = {"pdf"}

    # Stage 1 only needs the extracted text, so an upload is deleted as soon as
    # it has been read. Anything left behind by a crash is purged at startup.
    KEEP_UPLOADED_FILES = False
    UPLOAD_RETENTION_SECONDS = DEFAULT_UPLOAD_RETENTION_SECONDS

    TESTING = False
    DEBUG = False


class DevConfig(Config):
    DEBUG = True
    # Development only: a throwaway key so `python run.py` works out of the box.
    # `create_app` overrides it whenever SECRET_KEY is set in the environment.
    SECRET_KEY = DEV_SECRET_KEY


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "testing-only-insecure-key"
    WTF_CSRF_ENABLED = False


class ProdConfig(Config):
    DEBUG = False


CONFIGS: dict[str, type[Config]] = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,
}

DEFAULT_CONFIG_NAME = "production"


def get_config(config_name: str | None) -> type[Config]:
    """Resolve a configuration name, defaulting to production.

    An unknown name raises instead of falling back, because falling back to
    development is exactly how a production deployment ends up serving the
    interactive debugger.
    """
    name = (config_name or DEFAULT_CONFIG_NAME).strip().lower()
    if name not in CONFIGS:
        raise ConfigurationError(
            f"Unknown FLASK_CONFIG {config_name!r}. Valid values are: {', '.join(sorted(CONFIGS))}."
        )
    return CONFIGS[name]


def validate_settings(config_name: str, settings: dict) -> None:
    """Refuse to start with a missing key or a debug-enabled production app."""
    if not settings.get("SECRET_KEY"):
        raise ConfigurationError(
            f"SECRET_KEY is not set. Set the SECRET_KEY environment variable "
            f"before starting ResumeIQ with the {config_name} configuration."
        )
    if config_name == "production":
        if settings.get("DEBUG"):
            raise ConfigurationError("DEBUG must stay off in the production configuration.")
        if settings.get("SECRET_KEY") == DEV_SECRET_KEY:
            raise ConfigurationError("The development SECRET_KEY must not be used in production.")
