from flask import Flask, jsonify

from app.extensions import db as db  # noqa: F401
from app.extensions import init_db
from config import config


def create_app(config_name="development"):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    _register_extensions(app)
    _register_blueprints(app)
    _register_routes(app)

    return app


def _register_extensions(app):
    """Register Flask extensions."""
    init_db(app)


def _register_blueprints(app):
    """Register Flask blueprints."""
    from app.interface.web import web_bp

    app.register_blueprint(web_bp)


def _register_routes(app):
    """Register application-wide routes."""

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})
