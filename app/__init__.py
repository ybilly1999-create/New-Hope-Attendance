"""Church attendance application factory."""
import os
from datetime import datetime, time as dtime
from flask import Flask
from dotenv import load_dotenv

from .models import db
from .routes import bp as main_bp
from .admin import admin_bp
from .api import api_bp

load_dotenv()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance directory exists for SQLite
    os.makedirs(app.instance_path, exist_ok=True)

    # Database URL: prefer DATABASE_URL env, otherwise SQLite in instance dir
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        database_url = f"sqlite:///{os.path.join(app.instance_path, 'attendance.db')}"
    # Render's older Postgres URLs use postgres:// — SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin"),
        CHURCH_NAME="新希望浸信會陽光堂",
    )

    db.init_app(app)

    # Create tables on first run (idempotent)
    with app.app_context():
        db.create_all()
        _ensure_default_settings()

    # Make church name available in all templates
    @app.context_processor
    def inject_globals():
        from .models import Setting
        service_start = Setting.get("service_start_time", "10:00")
        return {
            "CHURCH_NAME": app.config["CHURCH_NAME"],
            "SERVICE_START_TIME": service_start,
            "current_year": datetime.now().year,
        }

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


def _ensure_default_settings():
    """Initialize default settings on first launch."""
    from .models import Setting
    defaults = {
        "service_start_time": os.environ.get("SERVICE_START_TIME", "10:00"),
    }
    for key, value in defaults.items():
        if Setting.get(key) is None:
            Setting.set(key, value)
    db.session.commit()
