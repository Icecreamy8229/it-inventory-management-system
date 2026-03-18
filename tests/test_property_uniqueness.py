# Feature: equipment-inventory-management, Property 3: Uniqueness enforcement for asset tag and serial number
# **Validates: Requirements 1.4, 1.6**

import pytest
from datetime import date

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

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
        cat = Category(name="TestCategory")
        db.session.add(cat)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


# Strategies for generating valid equipment data fields
asset_tag_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

serial_number_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

name_st = st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")
manufacturer_st = st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != "")
model_st = st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != "")


def make_equipment_data(asset_tag, serial_number):
    """Build a valid equipment data dict with the given asset_tag and serial_number."""
    return {
        "asset_tag": asset_tag,
        "name": "Test Item",
        "category": "TestCategory",
        "manufacturer": "TestMfg",
        "model": "TestModel",
        "serial_number": serial_number,
        "purchase_date": date(2024, 1, 1),
        "purchase_cost": 100.0,
        "warranty_expiration_date": date(2027, 1, 1),
    }


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    tag1=asset_tag_st,
    sn1=serial_number_st,
    sn2=serial_number_st,
)
def test_duplicate_asset_tag_rejected(app, tag1, sn1, sn2):
    """For any existing equipment record, a second registration with the same
    asset_tag should be rejected with an error identifying the duplicate field."""
    assume(sn1 != sn2)

    with app.app_context():
        # Insert first record
        equip = Equipment(**make_equipment_data(tag1, sn1))
        db.session.add(equip)
        db.session.commit()

        try:
            # Second record shares asset_tag but has a different serial_number
            second_data = make_equipment_data(tag1, sn2)
            errors = validate_equipment_data(second_data)
            assert "asset_tag already exists" in errors
        finally:
            db.session.delete(equip)
            db.session.commit()


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    tag1=asset_tag_st,
    tag2=asset_tag_st,
    sn1=serial_number_st,
)
def test_duplicate_serial_number_rejected(app, tag1, tag2, sn1):
    """For any existing equipment record, a second registration with the same
    serial_number should be rejected with an error identifying the duplicate field."""
    assume(tag1 != tag2)

    with app.app_context():
        # Insert first record
        equip = Equipment(**make_equipment_data(tag1, sn1))
        db.session.add(equip)
        db.session.commit()

        try:
            # Second record shares serial_number but has a different asset_tag
            second_data = make_equipment_data(tag2, sn1)
            errors = validate_equipment_data(second_data)
            assert "serial_number already exists" in errors
        finally:
            db.session.delete(equip)
            db.session.commit()
