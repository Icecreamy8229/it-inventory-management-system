import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
csrf = CSRFProtect()


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
    csrf.init_app(app)

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

        # Lightweight migration: add columns that may not exist yet
        _migrate_add_columns(app)

        # Migrate legacy equipment_history into equipment_snapshot
        _migrate_history_to_snapshots(app)

        # Seed from config.yaml on first startup
        from services.seed_service import seed_from_config
        seed_from_config()

    return app


def _migrate_add_columns(app):
    """Add any missing columns to existing tables (SQLite doesn't auto-migrate)."""
    import sqlalchemy

    with db.engine.connect() as conn:
        inspector = sqlalchemy.inspect(db.engine)

        system_config_columns = [c["name"] for c in inspector.get_columns("system_config")]
        if "site_url" not in system_config_columns:
            conn.execute(sqlalchemy.text(
                "ALTER TABLE system_config ADD COLUMN site_url VARCHAR(500)"
            ))
            conn.commit()

        equipment_columns = [c["name"] for c in inspector.get_columns("equipment")]
        if "image_filename" not in equipment_columns:
            conn.execute(sqlalchemy.text(
                "ALTER TABLE equipment ADD COLUMN image_filename VARCHAR(300)"
            ))
            conn.commit()

        # Add has_full_data to equipment_snapshot if missing
        if "equipment_snapshot" in inspector.get_table_names():
            snapshot_columns = [c["name"] for c in inspector.get_columns("equipment_snapshot")]
            if "has_full_data" not in snapshot_columns:
                conn.execute(sqlalchemy.text(
                    "ALTER TABLE equipment_snapshot ADD COLUMN has_full_data BOOLEAN NOT NULL DEFAULT 1"
                ))
                conn.commit()

        # Migration: relax NOT NULL constraints on optional equipment fields.
        # SQLite cannot ALTER COLUMN, so we rebuild the table if needed.
        _migrate_equipment_nullable(conn, inspector)


def _migrate_equipment_nullable(conn, inspector):
    """Rebuild the equipment table so that category, manufacturer, model,
    serial_number, and purchase_cost columns allow NULL values."""
    import sqlalchemy

    columns_info = {c["name"]: c for c in inspector.get_columns("equipment")}

    # Fields that should now be nullable (were previously NOT NULL)
    should_be_nullable = ["category", "manufacturer", "model", "serial_number", "purchase_cost"]

    needs_migration = any(
        col in columns_info and columns_info[col].get("nullable") is False
        for col in should_be_nullable
    )

    if not needs_migration:
        return

    conn.execute(sqlalchemy.text("PRAGMA foreign_keys = OFF"))
    conn.execute(sqlalchemy.text("""
        CREATE TABLE equipment_new (
            id INTEGER PRIMARY KEY,
            asset_tag VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(50),
            manufacturer VARCHAR(100),
            model VARCHAR(100),
            serial_number VARCHAR(100) UNIQUE,
            purchase_date DATE,
            purchase_cost FLOAT,
            warranty_expiration_date DATE,
            status VARCHAR(20) NOT NULL DEFAULT 'Available',
            assignee VARCHAR(200),
            location VARCHAR(300),
            notes TEXT,
            image_filename VARCHAR(300),
            created_at DATETIME,
            updated_at DATETIME
        )
    """))

    # Copy all existing data
    conn.execute(sqlalchemy.text("""
        INSERT INTO equipment_new
        SELECT id, asset_tag, name, category, manufacturer, model,
               serial_number, purchase_date, purchase_cost,
               warranty_expiration_date, status, assignee, location,
               notes, image_filename, created_at, updated_at
        FROM equipment
    """))

    conn.execute(sqlalchemy.text("DROP TABLE equipment"))
    conn.execute(sqlalchemy.text("ALTER TABLE equipment_new RENAME TO equipment"))
    conn.execute(sqlalchemy.text("PRAGMA foreign_keys = ON"))
    conn.commit()



def _migrate_history_to_snapshots(app):
    """Move legacy equipment_history rows into equipment_snapshot, then drop the old table."""
    import sqlalchemy

    with db.engine.connect() as conn:
        inspector = sqlalchemy.inspect(db.engine)
        if "equipment_history" not in inspector.get_table_names():
            return

        # Copy rows that haven't been migrated yet
        rows = conn.execute(sqlalchemy.text(
            "SELECT id, equipment_id, change_date, change_type, description, changed_by "
            "FROM equipment_history"
        )).fetchall()

        for row in rows:
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO equipment_snapshot "
                    "(equipment_id, snapshot_date, change_type, description, changed_by, has_full_data) "
                    "VALUES (:eid, :sd, :ct, :desc, :cb, 0)"
                ),
                {
                    "eid": row[1],
                    "sd": row[2],
                    "ct": row[3],
                    "desc": row[4],
                    "cb": row[5],
                },
            )

        conn.execute(sqlalchemy.text("DROP TABLE equipment_history"))
        conn.commit()
