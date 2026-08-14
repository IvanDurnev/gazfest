import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_project_path(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT / 'gaz.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/1",
    )
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/2",
    )

    MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "")
    MAX_WEBHOOK_SECRET = os.getenv("MAX_WEBHOOK_SECRET", "")
    MAX_API_BASE_URL = os.getenv(
        "MAX_API_BASE_URL",
        "https://platform-api2.max.ru",
    ).rstrip("/")
    MAX_CA_CERT_PATH = resolve_project_path(
        os.getenv(
            "MAX_CA_CERT_PATH",
            "certs/russian_trusted_root_ca.pem",
        )
    )
    MAX_WEBHOOK_PATH = os.getenv("MAX_WEBHOOK_PATH", "/max/webhook")
    MAX_MINIAPP_AUTH_MAX_AGE_SECONDS = int(
        os.getenv("MAX_MINIAPP_AUTH_MAX_AGE_SECONDS", "3600")
    )

    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "500"))
