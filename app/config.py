import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL


BASE_DIR = Path(__file__).resolve().parent.parent

environment = os.getenv("FLASK_ENVIRONMENT", "development").lower()

if environment not in {"development", "production", "testing"}:
    raise ValueError(f"Unsupported environment: {environment}")

env_file = {
    "development": ".env.development",
    "production": ".env.production",
    "testing": ".env.testing",
}[environment]

load_dotenv(BASE_DIR / env_file, override=False)


def get_database_url():
    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    ).render_as_string(hide_password=False)


class BaseConfig:

    SQLALCHEMY_DATABASE_URI = get_database_url()

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_ECHO = (
        os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    )

    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            raise ValueError("Production SECRET_KEY must be at least 32 characters")

        if not os.getenv("DB_PASSWORD"):
            raise ValueError("Production DB_PASSWORD is required")


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
