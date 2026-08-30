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
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
