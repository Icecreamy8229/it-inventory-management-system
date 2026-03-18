import os
import io

import pytest

from app import create_app, db
from models import SystemConfig, Category, User
from services.config_service import ConfigService


@pytest.fixture
def app(tmp_path):
    """Create a test Flask application with an in-memory database and temp upload dir."""
    upload_dir = str(tmp_path / "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app = create_app(
        config_overrides={
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
            "UPLOAD_PATH": upload_dir,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def service(app):
    with app.app_context():
        yield ConfigService()


class FakeFile:
    """Minimal file-like object mimicking werkzeug FileStorage."""

    def __init__(self, filename="logo.png", content=b"fake-image-data"):
        self.filename = filename
        self._content = content

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self._content)


class TestIsSetupComplete:
    def test_false_when_no_config(self, service):
        assert service.is_setup_complete() is False

    def test_false_when_setup_not_complete(self, service, app):
        with app.app_context():
            config = SystemConfig(company_name="Test", app_title="App", setup_complete=False)
            db.session.add(config)
            db.session.commit()
        assert service.is_setup_complete() is False

    def test_true_when_setup_complete(self, service, app):
        with app.app_context():
            config = SystemConfig(company_name="Test", app_title="App", setup_complete=True)
            db.session.add(config)
            db.session.commit()
        assert service.is_setup_complete() is True


class TestGetConfig:
    def test_returns_none_when_no_config(self, service):
        assert service.get_config() is None

    def test_returns_config_when_exists(self, service, app):
        with app.app_context():
            config = SystemConfig(company_name="Acme", app_title="Inventory", setup_complete=True)
            db.session.add(config)
            db.session.commit()
        result = service.get_config()
        assert result is not None
        assert result.company_name == "Acme"
        assert result.app_title == "Inventory"


class TestSaveSetup:
    def test_creates_config_with_setup_complete(self, service):
        config = service.save_setup("Acme", "Inventory")
        assert config.company_name == "Acme"
        assert config.app_title == "Inventory"
        assert config.setup_complete is True
        assert config.id is not None

    def test_creates_default_categories_when_none_provided(self, service):
        service.save_setup("Acme", "Inventory")
        categories = Category.query.all()
        names = [c.name for c in categories]
        assert "Laptops" in names
        assert "Monitors" in names
        assert "Peripherals" in names
        assert "Servers" in names
        assert "Networking" in names

    def test_creates_custom_categories(self, service):
        service.save_setup("Acme", "Inventory", categories=["Phones", "Tablets"])
        categories = Category.query.all()
        names = [c.name for c in categories]
        assert names == ["Phones", "Tablets"]

    def test_creates_admin_user(self, service):
        service.save_setup("Acme", "Inventory", admin_username="admin", admin_password="secret")
        user = User.query.filter_by(username="admin").first()
        assert user is not None
        assert user.role == "admin"
        assert user.password_hash != "secret"

    def test_saves_logo_file(self, service, app):
        logo = FakeFile(filename="company_logo.png")
        config = service.save_setup("Acme", "Inventory", logo_file=logo)
        assert config.logo_path == "company_logo.png"
        upload_path = app.config["UPLOAD_PATH"]
        assert os.path.exists(os.path.join(upload_path, "company_logo.png"))

    def test_no_logo_when_not_provided(self, service):
        config = service.save_setup("Acme", "Inventory")
        assert config.logo_path is None

    def test_no_admin_when_credentials_not_provided(self, service):
        service.save_setup("Acme", "Inventory")
        users = User.query.all()
        assert len(users) == 0


class TestUpdateConfig:
    def test_updates_company_name(self, service):
        service.save_setup("Acme", "Inventory")
        updated = service.update_config(company_name="NewCo")
        assert updated.company_name == "NewCo"
        assert updated.app_title == "Inventory"

    def test_updates_app_title(self, service):
        service.save_setup("Acme", "Inventory")
        updated = service.update_config(app_title="New Title")
        assert updated.app_title == "New Title"
        assert updated.company_name == "Acme"

    def test_updates_logo(self, service, app):
        service.save_setup("Acme", "Inventory")
        logo = FakeFile(filename="new_logo.png")
        updated = service.update_config(logo_file=logo)
        assert updated.logo_path == "new_logo.png"
        upload_path = app.config["UPLOAD_PATH"]
        assert os.path.exists(os.path.join(upload_path, "new_logo.png"))

    def test_raises_when_no_config(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.update_config(company_name="NewCo")

    def test_leaves_unchanged_fields_intact(self, service):
        service.save_setup("Acme", "Inventory")
        updated = service.update_config()
        assert updated.company_name == "Acme"
        assert updated.app_title == "Inventory"
