import pytest

from app import create_app
from app.config import Config
from app.extensions import db


class TestConfig(Config):
    TESTING = True
    MAX_BOT_TOKEN = "test-bot-token"
    MAX_WEBHOOK_SECRET = "test-secret"
    MAX_MINIAPP_AUTH_MAX_AGE_SECONDS = 3600
    REDIS_URL = "redis://localhost:6379/15"
    SQLALCHEMY_DATABASE_URI = "sqlite://"


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
