from flask import Blueprint

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    return "Academy Management System"
