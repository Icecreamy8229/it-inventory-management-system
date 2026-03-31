import pytest
from datetime import date

from app import create_app, db
from models import Category, Equipment
from services.validation import validate_equipment_data


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
def setup_category(app):
    """Add a default category for tests."""
    with app.app_context():
        cat = Category(name="Laptops")
        db.session.add(cat)
        db.session.commit()
        yield cat


def _valid_data():
    return {
        "asset_tag": "AT-001",
        "name": "Test Laptop",
        "category": "Laptops",
        "manufacturer": "Dell",
        "model": "XPS 15",
        "serial_number": "SN-001",
        "purchase_date": date(2024, 1, 1),
        "purchase_cost": 1500.00,
        "warranty_expiration_date": date(2027, 1, 1),
    }


class TestRequiredFields:
    def test_valid_data_returns_no_errors(self, app, setup_category):
        with app.app_context():
            errors = validate_equipment_data(_valid_data())
            assert errors == []

    def test_missing_single_required_field(self, app, setup_category):
        required = [
            "asset_tag",
            "name",
        ]
        for field in required:
            with app.app_context():
                data = _valid_data()
                del data[field]
                errors = validate_equipment_data(data)
                assert f"{field} is required" in errors, f"Expected error for missing {field}"

    def test_empty_string_field_is_required(self, app, setup_category):
        with app.app_context():
            data = _valid_data()
            data["asset_tag"] = "   "
            errors = validate_equipment_data(data)
            assert "asset_tag is required" in errors

    def test_all_fields_missing(self, app, setup_category):
        with app.app_context():
            errors = validate_equipment_data({})
            assert len(errors) == 2

    def test_optional_fields_not_required(self, app, setup_category):
        with app.app_context():
            data = _valid_data()
            # location and notes are optional, should not cause errors
            errors = validate_equipment_data(data)
            assert errors == []


class TestAssetTagUniqueness:
    def test_duplicate_asset_tag_rejected(self, app, setup_category):
        with app.app_context():
            equip = Equipment(**_valid_data())
            db.session.add(equip)
            db.session.commit()

            data = _valid_data()
            data["serial_number"] = "SN-002"
            errors = validate_equipment_data(data)
            assert "asset_tag already exists" in errors

    def test_duplicate_asset_tag_skipped_on_update(self, app, setup_category):
        with app.app_context():
            equip = Equipment(**_valid_data())
            db.session.add(equip)
            db.session.commit()

            errors = validate_equipment_data(
                _valid_data(), is_update=True, equipment_id=equip.id
            )
            assert "asset_tag already exists" not in errors


class TestSerialNumberUniqueness:
    def test_duplicate_serial_number_rejected(self, app, setup_category):
        with app.app_context():
            equip = Equipment(**_valid_data())
            db.session.add(equip)
            db.session.commit()

            data = _valid_data()
            data["asset_tag"] = "AT-002"
            errors = validate_equipment_data(data)
            assert "serial_number already exists" in errors

    def test_duplicate_serial_number_skipped_on_update(self, app, setup_category):
        with app.app_context():
            equip = Equipment(**_valid_data())
            db.session.add(equip)
            db.session.commit()

            errors = validate_equipment_data(
                _valid_data(), is_update=True, equipment_id=equip.id
            )
            assert "serial_number already exists" not in errors


class TestCategoryValidation:
    def test_nonexistent_category_rejected(self, app, setup_category):
        with app.app_context():
            data = _valid_data()
            data["category"] = "NonExistent"
            errors = validate_equipment_data(data)
            assert "category 'NonExistent' does not exist" in errors

    def test_existing_category_accepted(self, app, setup_category):
        with app.app_context():
            errors = validate_equipment_data(_valid_data())
            assert not any("category" in e for e in errors)
