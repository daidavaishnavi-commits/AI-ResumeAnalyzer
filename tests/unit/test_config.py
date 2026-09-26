from __future__ import annotations

import pytest

from app import create_app
from app.config import DEV_SECRET_KEY, ConfigurationError, DevConfig, ProdConfig, get_config


def test_valid_names_resolve():
    assert get_config("development") is DevConfig
    assert get_config("production") is ProdConfig
    assert get_config("PRODUCTION") is ProdConfig


def test_unknown_name_is_rejected():
    with pytest.raises(ConfigurationError, match="Unknown FLASK_CONFIG"):
        get_config("developmnet")


def test_missing_name_defaults_to_production():
    assert get_config(None) is ProdConfig


def test_development_app_starts_without_a_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    app = create_app("development")

    assert app.config["DEBUG"] is True
    assert app.config["SECRET_KEY"] == DEV_SECRET_KEY


def test_production_requires_a_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="SECRET_KEY"):
        create_app("production")


def test_production_uses_the_environment_secret_key_and_no_debug(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-real-production-secret")
    app = create_app("production")

    assert app.config["SECRET_KEY"] == "a-real-production-secret"
    assert app.config["DEBUG"] is False
    assert app.debug is False


def test_production_rejects_the_development_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", DEV_SECRET_KEY)
    with pytest.raises(ConfigurationError):
        create_app("production")


def test_unknown_flask_config_env_does_not_fall_back_to_development(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "prod")
    with pytest.raises(ConfigurationError):
        create_app()


def test_missing_flask_config_env_does_not_enable_debug(monkeypatch):
    monkeypatch.delenv("FLASK_CONFIG", raising=False)
    monkeypatch.setenv("SECRET_KEY", "a-real-production-secret")

    app = create_app()

    assert app.config["DEBUG"] is False


def test_run_module_does_not_force_debug():
    source = (__import__("pathlib").Path(__file__).resolve().parents[2] / "run.py").read_text()
    assert "debug=True" not in source
