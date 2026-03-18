# Feature: equipment-inventory-management, Property 20: Category add/remove round-trip
# **Validates: Requirements 10.2, 10.3**

import pytest

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app import create_app, db
from models import Category
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


# Strategy for generating valid category names: non-empty, printable strings
category_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=category_name_st)
def test_category_add_remove_round_trip(app, name):
    """For any valid category name not already in the Category table, adding it
    should result in it appearing in the category list. Removing it should result
    in it no longer appearing in the category list."""
    with app.app_context():
        service = CategoryService()

        # Ensure the name doesn't already exist (clean up from prior iterations)
        existing = Category.query.filter_by(name=name).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        # Add the category
        created = service.add_category(name)

        try:
            # Verify it appears in the list
            names_after_add = [c.name for c in service.list_categories()]
            assert name in names_after_add, (
                f"Category '{name}' should appear after adding"
            )

            # Delete the category
            service.delete_category(created.id)

            # Verify it no longer appears in the list
            names_after_delete = [c.name for c in service.list_categories()]
            assert name not in names_after_delete, (
                f"Category '{name}' should not appear after deletion"
            )
        finally:
            # Clean up in case of assertion failure mid-test
            leftover = Category.query.filter_by(name=name).first()
            if leftover:
                db.session.delete(leftover)
                db.session.commit()


# Feature: equipment-inventory-management, Property 21: Category deletion protection
# **Validates: Requirements 10.4**

from datetime import date
from models import Equipment


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=category_name_st)
def test_category_deletion_protection(app, name):
    """For any category that is referenced by at least one Equipment record,
    attempting to delete that category should be rejected, and the category
    should remain in the Category table."""
    with app.app_context():
        service = CategoryService()

        # Clean up any pre-existing data with this name
        existing_cat = Category.query.filter_by(name=name).first()
        if existing_cat:
            # Remove any equipment referencing this category first
            Equipment.query.filter_by(category=name).delete()
            db.session.delete(existing_cat)
            db.session.commit()

        # 1. Add the category
        created = service.add_category(name)
        cat_id = created.id

        # 2. Create an Equipment record that references this category
        equipment = Equipment(
            asset_tag=f"AT-{cat_id}-{name[:10]}",
            name="Test Equipment",
            category=name,
            manufacturer="TestMfg",
            model="TestModel",
            serial_number=f"SN-{cat_id}-{name[:10]}",
            purchase_date=date(2024, 1, 1),
            purchase_cost=100.0,
            warranty_expiration_date=date(2025, 1, 1),
            status="Available",
        )
        db.session.add(equipment)
        db.session.commit()

        try:
            # 3. Attempt to delete the category — should be rejected
            with pytest.raises(ValueError, match="in use"):
                service.delete_category(cat_id)

            # 4. Assert the category still exists
            cat_names = [c.name for c in service.list_categories()]
            assert name in cat_names, (
                f"Category '{name}' should still exist after failed deletion"
            )
        finally:
            # Clean up: remove equipment first, then category
            Equipment.query.filter_by(category=name).delete()
            leftover = Category.query.filter_by(name=name).first()
            if leftover:
                db.session.delete(leftover)
            db.session.commit()
