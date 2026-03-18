import pytest
from app import create_app, db
from models import Category, Equipment
from services.category_service import CategoryService


@pytest.fixture
def app():
    """Create a test Flask application with an in-memory database."""
    app = create_app(
        config_overrides={
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def service(app):
    """Return a CategoryService instance within app context."""
    with app.app_context():
        yield CategoryService()


class TestGetDefaultCategories:
    def test_returns_expected_defaults(self, service):
        defaults = service.get_default_categories()
        assert defaults == ["Laptops", "Monitors", "Peripherals", "Servers", "Networking"]

    def test_returns_list_of_strings(self, service):
        defaults = service.get_default_categories()
        assert all(isinstance(name, str) for name in defaults)


class TestListCategories:
    def test_empty_initially(self, service):
        assert service.list_categories() == []

    def test_returns_added_categories(self, service):
        service.add_category("Laptops")
        service.add_category("Monitors")
        categories = service.list_categories()
        names = [c.name for c in categories]
        assert "Laptops" in names
        assert "Monitors" in names
        assert len(categories) == 2


class TestAddCategory:
    def test_adds_new_category(self, service):
        cat = service.add_category("Laptops")
        assert cat.name == "Laptops"
        assert cat.id is not None

    def test_rejects_duplicate_name(self, service):
        service.add_category("Laptops")
        with pytest.raises(ValueError, match="already exists"):
            service.add_category("Laptops")

    def test_allows_different_names(self, service):
        service.add_category("Laptops")
        cat2 = service.add_category("Monitors")
        assert cat2.name == "Monitors"


class TestDeleteCategory:
    def test_deletes_unused_category(self, service):
        cat = service.add_category("Laptops")
        service.delete_category(cat.id)
        assert service.list_categories() == []

    def test_rejects_delete_if_in_use(self, app, service):
        with app.app_context():
            cat = service.add_category("Laptops")
            from datetime import date

            equip = Equipment(
                asset_tag="AT-001",
                name="Test Laptop",
                category="Laptops",
                manufacturer="Dell",
                model="XPS 15",
                serial_number="SN-001",
                purchase_date=date(2024, 1, 1),
                purchase_cost=1500.00,
                warranty_expiration_date=date(2027, 1, 1),
            )
            db.session.add(equip)
            db.session.commit()

            with pytest.raises(ValueError, match="in use"):
                service.delete_category(cat.id)

            # Category should still exist
            assert len(service.list_categories()) == 1
