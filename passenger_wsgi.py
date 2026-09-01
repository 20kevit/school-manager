import os
from pathlib import Path


def _load_env_fallback():
    """Load .env file if key environment variables are not already set."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_fallback()

from app import create_app  # noqa: E402

app = create_app("production")

application = app
