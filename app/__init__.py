from flask import Flask

from app.cli import register_commands
from app.config import Config
from app.extensions import db, migrate
from app.routes import api


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(api)
    register_commands(app)
    return app
