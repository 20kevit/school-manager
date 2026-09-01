import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SMS
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "")
    SMS_API_KEY = os.getenv("SMS_API_KEY", "")
    SMS_SENDER = os.getenv("SMS_SENDER", "")
    SMS_API_URL = os.getenv("SMS_API_URL", "")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Bale
    BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")

    # Email
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")

    # File Management
    FILE_STORAGE_BACKEND = os.getenv("FILE_STORAGE_BACKEND", "local")
    FILE_STORAGE_PATH = os.getenv("FILE_STORAGE_PATH", "")
    FILE_MAX_UPLOAD_SIZE = int(os.getenv("FILE_MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))

    # ZarinPal Payment Gateway
    ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "")
    ZARINPAL_SANDBOX = os.getenv("ZARINPAL_SANDBOX", "true").lower() == "true"

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///school_manager_dev.db",
    )


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    FILE_STORAGE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_storage"
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 8 * 3600  # 8 hours

    @staticmethod
    def init_app(app):
        db_url = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
        if db_url.startswith("mysql"):
            app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
            app.config["SQLALCHEMY_ENGINE_OPTIONS"].update(
                {
                    "pool_pre_ping": True,
                    "connect_args": {"charset": "utf8mb4"},
                }
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
