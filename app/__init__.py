"""ResumeIQ application factory."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, render_template

from app.config import DEFAULT_CONFIG_NAME, get_config, validate_settings
from app.extensions import csrf
from app.services import upload_service


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    config_name = (config_name or os.environ.get("FLASK_CONFIG") or DEFAULT_CONFIG_NAME).lower()
    app.config.from_object(get_config(config_name))

    secret_key = os.environ.get("SECRET_KEY")
    if secret_key:
        app.config["SECRET_KEY"] = secret_key
    validate_settings(config_name, app.config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    upload_service.purge_old_uploads(
        app.config["UPLOAD_FOLDER"], app.config["UPLOAD_RETENTION_SECONDS"]
    )

    csrf.init_app(app)

    from app.routes.analyze import analyze_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(analyze_bp)

    register_error_handlers(app)

    if not app.testing:
        logging.basicConfig(level=logging.INFO)

    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_error):
        max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return render_template("errors/413.html", max_mb=max_mb), 413

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("unhandled error: %s", error)
        return render_template("errors/500.html"), 500
