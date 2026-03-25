import os

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from models import SystemConfig, Category
from services.category_service import CategoryService
from services.user_service import UserService


class ConfigService:
    def is_setup_complete(self) -> bool:
        """Check if the system has been configured."""
        config = SystemConfig.query.first()
        return config is not None and config.setup_complete

    def get_config(self) -> SystemConfig | None:
        """Retrieve the current system configuration."""
        return SystemConfig.query.first()

    def save_setup(
        self,
        company_name: str,
        app_title: str,
        logo_file=None,
        site_url: str = "",
        categories: list[str] = None,
        admin_username: str = None,
        admin_password: str = None,
    ) -> SystemConfig:
        """Save initial setup configuration. Creates SystemConfig, Category records, and initial Admin user."""
        logo_path = None
        if logo_file:
            logo_path = self._save_logo(logo_file)

        config = SystemConfig(
            company_name=company_name,
            app_title=app_title,
            logo_path=logo_path,
            site_url=site_url or "",
            setup_complete=True,
        )
        db.session.add(config)

        # Create category records
        category_names = categories if categories is not None else CategoryService().get_default_categories()
        for name in category_names:
            existing = Category.query.filter_by(name=name).first()
            if not existing:
                db.session.add(Category(name=name))

        # Create initial admin user
        if admin_username and admin_password:
            user_service = UserService()
            user_service.create_user(admin_username, admin_password, role="admin")

        db.session.commit()
        return config

    def update_config(
        self,
        company_name: str = None,
        app_title: str = None,
        logo_file=None,
        site_url: str = None,
    ) -> SystemConfig:
        """Update branding settings."""
        config = SystemConfig.query.first()
        if config is None:
            raise ValueError("System configuration not found")

        if company_name is not None:
            config.company_name = company_name
        if app_title is not None:
            config.app_title = app_title
        if site_url is not None:
            config.site_url = site_url
        if logo_file:
            config.logo_path = self._save_logo(logo_file)

        db.session.commit()
        return config

    def _save_logo(self, logo_file) -> str:
        """Save a logo file to the upload directory and return the filename."""
        upload_path = current_app.config["UPLOAD_PATH"]
        filename = secure_filename(logo_file.filename)
        filepath = os.path.join(upload_path, filename)
        logo_file.save(filepath)
        return filename
