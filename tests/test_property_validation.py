# Feature: equipment-inventory-management, Property 4: Validation rejects incomplete data
# **Validates: Requirements 1.5, 3.2**

import pytest
from datetime import date

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app import create_app, db
from models import Category
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
        cat = Category(name="TestCategory")
        db.session.add(cat)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


REQUIRED_FIELDS = [
    "asset_tag",
    "name",
]


def make_complete_equipment_data():
    """Build a complete valid equipment data dict with all required fields."""
    return {
        "asset_tag": "AT-001",
        "name": "Test Laptop",
        "category": "TestCategory",
        "manufacturer": "TestMfg",
        "model": "TestModel",
        "serial_number": "SN-001",
        "purchase_date": date(2024, 1, 1),
        "purchase_cost": 999.99,
        "warranty_expiration_date": date(2027, 1, 1),
    }


# Strategy: generate a non-empty subset of required fields to remove
fields_to_remove_st = st.lists(
    st.sampled_from(REQUIRED_FIELDS),
    min_size=1,
    max_size=len(REQUIRED_FIELDS),
    unique=True,
)


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(fields_to_remove=fields_to_remove_st)
def test_validation_rejects_incomplete_data(app, fields_to_remove):
    """For any subset of required equipment fields that is missing at least one
    required field, submitting the form should be rejected, and the returned
    errors should identify each missing required field."""
    with app.app_context():
        data = make_complete_equipment_data()

        # Remove the randomly selected required fields
        for field in fields_to_remove:
            del data[field]

        errors = validate_equipment_data(data)

        # Validation must return errors
        assert len(errors) > 0, (
            f"Expected validation errors when fields {fields_to_remove} are missing, "
            f"but got none"
        )

        # Each missing field must be identified in the errors
        for field in fields_to_remove:
            assert any(field in error for error in errors), (
                f"Missing field '{field}' was not identified in errors: {errors}"
            )
