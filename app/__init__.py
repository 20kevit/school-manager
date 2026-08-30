import os

from flask import Flask, jsonify
from flask_login import LoginManager

from app.extensions import db as db  # noqa: F401
from app.extensions import init_db
from config import config

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "error"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(config_name="development"):
    """Application factory."""
    app = Flask(__name__, template_folder=os.path.join(PROJECT_ROOT, "templates"))
    app.config.from_object(config[config_name])

    _register_extensions(app)
    _register_blueprints(app)
    _register_routes(app)

    return app


def _register_extensions(app):
    """Register Flask extensions."""
    init_db(app)
    login_manager.init_app(app)

    from app.infrastructure.database.models import UserModel

    @login_manager.user_loader
    def load_user(user_id: str):
        return UserModel.query.get(int(user_id))


def _register_blueprints(app):
    """Register Flask blueprints."""
    from app.interface.web import web_bp
    from app.interface.web.academy.routes import academy_bp
    from app.interface.web.activity.routes import activity_bp
    from app.interface.web.assessment.routes import assessment_bp
    from app.interface.web.attendance.routes import attendance_bp
    from app.interface.web.auth import auth_bp
    from app.interface.web.enrollment.routes import enrollment_bp
    from app.interface.web.finance.routes import finance_bp
    from app.interface.web.portal.routes import portal_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(academy_bp)
    app.register_blueprint(enrollment_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(portal_bp)


def _register_routes(app):
    """Register application-wide routes."""

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})
