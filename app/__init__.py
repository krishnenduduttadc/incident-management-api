from flask import Flask
import os
from flask_cors import CORS

from app.config import (
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
)

from app.extensions import db, migrate


def create_app(environment=None):

    app = Flask(__name__)

    # Determine environment
    environment = (
        environment or
        os.getenv("FLASK_ENVIRONMENT", "development")
    ).lower()

    # Environment configuration mapping
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }

    if environment not in configs:
        raise ValueError(f"Invalid environment: {environment}")

    config_class = configs[environment]

    # Validate production configuration
    if environment == "production":
        config_class.validate()

    # Load configuration
    app.config.from_object(config_class)


    # cors
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5500"
                ]
            }
        }
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Flask-Migrate can discover them
    from app import models

    # Register health API
    from app.routes.health import health_bp
    app.register_blueprint(
        health_bp,
        url_prefix="/api"
    )

    # Register CRUD APIs for reference tables
    from app.routes.resources import resources_bp
    app.register_blueprint(
        resources_bp,
        url_prefix="/api"
    )

    # Register incident, assignment, status and history APIs
    from app.routes.incidents import incidents_bp
    app.register_blueprint(
        incidents_bp,
        url_prefix="/api"
    )

    return app