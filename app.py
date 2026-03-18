import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"


def create_app(config_overrides=None):
    """Flask application factory."""
    app = Flask(__name__)

    # Configuration
    database_path = os.environ.get("DATABASE_PATH", "data/equipment.db")
    upload_path = os.environ.get("UPLOAD_PATH", "data/uploads")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_PATH"] = upload_path

    if config_overrides:
        app.config.update(config_overrides)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure data directories exist (use config values which may have been overridden)
    effective_db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if effective_db_uri.startswith("sqlite:///"):
        effective_db_path = effective_db_uri[len("sqlite:///"):]
        db_dir = os.path.dirname(effective_db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    effective_upload_path = app.config["UPLOAD_PATH"]
    os.makedirs(effective_upload_path, exist_ok=True)

    # Register Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        from services.user_service import UserService
        return UserService().get_user_by_id(int(user_id))

    # Register context processor for templates
    @app.context_processor
    def inject_system_config():
        from models import SystemConfig
        config = SystemConfig.query.first()
        return dict(system_config=config)

    # Register middleware
    from middleware import register_middleware
    register_middleware(app)

    # Register routes
    from routes import register_routes
    register_routes(app)

    with app.app_context():
        # Import models so they are registered with SQLAlchemy before create_all
        import models  # noqa: F401
        db.create_all()

    return app

