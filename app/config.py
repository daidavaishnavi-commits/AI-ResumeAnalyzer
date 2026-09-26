"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(INSTANCE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES
    ALLOWED_EXTENSIONS = {"pdf"}

    TESTING = False
    DEBUG = False


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    WTF_CSRF_ENABLED = False


class ProdConfig(Config):
    pass


CONFIGS = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,
    "default": DevConfig,
}
