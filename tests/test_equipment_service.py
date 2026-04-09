import pytest
from datetime import date

from app import create_app, db
from models import Equipment, EquipmentSnapshot, Category
from services.equipment_service import EquipmentService


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
    """Return an EquipmentService instance within app context."""
    with app.app_context():
        yield EquipmentService()


@pytest.fixture
def sample_data(app):
    """Seed a category and return valid equipment data dict."""
    with app.app_context():
        db.session.add(Category(name="Laptops"))
        db.session.commit()
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


class TestCreateEquipment:
    def test_creates_equipment_with_correct_fields(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        assert equip.id is not None
        assert equip.asset_tag == "AT-001"
        assert equip.name == "Test Laptop"
        assert equip.category == "Laptops"
        assert equip.manufacturer == "Dell"
        assert equip.model == "XPS 15"
        assert equip.serial_number == "SN-001"
        assert equip.purchase_date == date(2024, 1, 1)
        assert equip.purchase_cost == 1500.00
        assert equip.warranty_expiration_date == date(2027, 1, 1)
        assert equip.status == "Available"

    def test_creates_history_entry(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        history = EquipmentSnapshot.query.filter_by(equipment_id=equip.id).all()
        assert len(history) == 1
        assert history[0].change_type == "Created"
        assert history[0].description == "Equipment record created"

    def test_optional_location_and_notes(self, service, sample_data):
        sample_data["location"] = "Building A, Room 101"
        sample_data["notes"] = "Has USB-C dock"
        equip = service.create_equipment(sample_data)
        assert equip.location == "Building A, Room 101"
        assert equip.notes == "Has USB-C dock"

    def test_location_and_notes_default_to_none(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        assert equip.location is None
        assert equip.notes is None

    def test_raises_on_missing_required_field(self, service, sample_data):
        del sample_data["asset_tag"]
        with pytest.raises(ValueError):
            service.create_equipment(sample_data)

    def test_raises_on_duplicate_asset_tag(self, service, sample_data):
        service.create_equipment(sample_data)
        sample_data["serial_number"] = "SN-002"
        with pytest.raises(ValueError):
            service.create_equipment(sample_data)

    def test_raises_on_duplicate_serial_number(self, service, sample_data):
        service.create_equipment(sample_data)
        sample_data["asset_tag"] = "AT-002"
        with pytest.raises(ValueError):
            service.create_equipment(sample_data)

    def test_raises_on_invalid_category(self, service, sample_data):
        sample_data["category"] = "NonExistent"
        with pytest.raises(ValueError):
            service.create_equipment(sample_data)

    def test_persists_to_database(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        fetched = db.session.get(Equipment, equip.id)
        assert fetched is not None
        assert fetched.asset_tag == "AT-001"


class TestUpdateEquipment:
    def test_updates_fields_successfully(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        update_data = dict(sample_data, name="Updated Laptop", model="XPS 17")
        updated = service.update_equipment(equip.id, update_data)
        assert updated.name == "Updated Laptop"
        assert updated.model == "XPS 17"

    def test_records_history_entry_with_changed_fields(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        update_data = dict(sample_data, name="New Name")
        service.update_equipment(equip.id, update_data)
        history = EquipmentSnapshot.query.filter_by(
            equipment_id=equip.id, change_type="Updated"
        ).all()
        assert len(history) == 1
        assert "name" in history[0].description
        assert history[0].name == "New Name"

    def test_no_history_when_no_fields_changed(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.update_equipment(equip.id, sample_data)
        updated_history = EquipmentSnapshot.query.filter_by(
            equipment_id=equip.id, change_type="Updated"
        ).all()
        assert len(updated_history) == 0

    def test_raises_value_error_for_nonexistent_equipment(self, service, sample_data):
        with pytest.raises(ValueError, match="Equipment not found"):
            service.update_equipment(9999, sample_data)

    def test_raises_value_error_on_invalid_data(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        bad_data = dict(sample_data, asset_tag="")
        with pytest.raises(ValueError):
            service.update_equipment(equip.id, bad_data)

    def test_optimistic_concurrency_passes_when_matching(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        ts = equip.updated_at
        update_data = dict(sample_data, name="Concurrent OK")
        updated = service.update_equipment(equip.id, update_data, expected_updated_at=ts)
        assert updated.name == "Concurrent OK"

    def test_optimistic_concurrency_raises_conflict_on_mismatch(self, service, sample_data):
        from datetime import datetime
        from exceptions import ConflictError

        equip = service.create_equipment(sample_data)
        stale_ts = datetime(2000, 1, 1)
        with pytest.raises(ConflictError):
            service.update_equipment(equip.id, sample_data, expected_updated_at=stale_ts)

    def test_update_optional_location_and_notes(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        update_data = dict(sample_data, location="Room 42", notes="Upgraded RAM")
        updated = service.update_equipment(equip.id, update_data)
        assert updated.location == "Room 42"
        assert updated.notes == "Upgraded RAM"

    def test_update_persists_to_database(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        update_data = dict(sample_data, name="Persisted Name")
        service.update_equipment(equip.id, update_data)
        fetched = db.session.get(Equipment, equip.id)
        assert fetched.name == "Persisted Name"


class TestGetEquipment:
    def test_returns_equipment_by_id(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        fetched = service.get_equipment(equip.id)
        assert fetched.id == equip.id
        assert fetched.asset_tag == "AT-001"

    def test_raises_value_error_for_nonexistent_id(self, service):
        with pytest.raises(ValueError, match="Equipment not found"):
            service.get_equipment(9999)


class TestDeleteEquipment:
    def test_deletes_equipment_record(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.delete_equipment(equip.id)
        assert db.session.get(Equipment, equip.id) is None

    def test_cascade_deletes_history_entries(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        equip_id = equip.id
        history_before = EquipmentSnapshot.query.filter_by(equipment_id=equip_id).all()
        assert len(history_before) >= 1
        service.delete_equipment(equip_id)
        history_after = EquipmentSnapshot.query.filter_by(equipment_id=equip_id).all()
        assert len(history_after) == 0

    def test_raises_value_error_for_nonexistent_id(self, service):
        with pytest.raises(ValueError, match="Equipment not found"):
            service.delete_equipment(9999)

    def test_equipment_not_retrievable_after_delete(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.delete_equipment(equip.id)
        with pytest.raises(ValueError, match="Equipment not found"):
            service.get_equipment(equip.id)


class TestAssignEquipment:
    def test_assigns_equipment_successfully(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        result = service.assign_equipment(equip.id, "John Doe")
        assert result.assignee == "John Doe"
        assert result.status == "Assigned"

    def test_records_assignment_history(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.assign_equipment(equip.id, "John Doe")
        history = EquipmentSnapshot.query.filter_by(
            equipment_id=equip.id, change_type="Assignment"
        ).all()
        assert len(history) == 1
        assert history[0].assignee == "John Doe"

    def test_rejects_assignment_when_retired(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        equip.status = "Retired"
        db.session.commit()
        with pytest.raises(ValueError, match="not available for assignment"):
            service.assign_equipment(equip.id, "John Doe")

    def test_rejects_assignment_when_under_repair(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        equip.status = "Under Repair"
        db.session.commit()
        with pytest.raises(ValueError, match="not available for assignment"):
            service.assign_equipment(equip.id, "John Doe")

    def test_raises_for_nonexistent_equipment(self, service):
        with pytest.raises(ValueError, match="Equipment not found"):
            service.assign_equipment(9999, "John Doe")

    def test_optimistic_concurrency_passes(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        ts = equip.updated_at
        result = service.assign_equipment(equip.id, "Jane", expected_updated_at=ts)
        assert result.assignee == "Jane"

    def test_optimistic_concurrency_raises_conflict(self, service, sample_data):
        from datetime import datetime
        from exceptions import ConflictError

        equip = service.create_equipment(sample_data)
        stale_ts = datetime(2000, 1, 1)
        with pytest.raises(ConflictError):
            service.assign_equipment(equip.id, "Jane", expected_updated_at=stale_ts)

    def test_reassign_records_previous_assignee(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.assign_equipment(equip.id, "Alice")
        service.assign_equipment(equip.id, "Bob")
        history = EquipmentSnapshot.query.filter_by(
            equipment_id=equip.id, change_type="Assignment"
        ).order_by(EquipmentSnapshot.id).all()
        assert len(history) == 2
        assert history[0].assignee == "Alice"
        assert history[1].assignee == "Bob"


class TestUnassignEquipment:
    def test_unassigns_equipment_successfully(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.assign_equipment(equip.id, "John Doe")
        result = service.unassign_equipment(equip.id)
        assert result.assignee is None
        assert result.status == "Available"

    def test_records_unassignment_history(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.assign_equipment(equip.id, "John Doe")
        service.unassign_equipment(equip.id)
        history = EquipmentSnapshot.query.filter_by(
            equipment_id=equip.id, change_type="Unassignment"
        ).all()
        assert len(history) == 1
        assert history[0].assignee is None

    def test_raises_for_nonexistent_equipment(self, service):
        with pytest.raises(ValueError, match="Equipment not found"):
            service.unassign_equipment(9999)

    def test_optimistic_concurrency_passes(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.assign_equipment(equip.id, "Jane")
        equip = service.get_equipment(equip.id)
        ts = equip.updated_at
        result = service.unassign_equipment(equip.id, expected_updated_at=ts)
        assert result.assignee is None

    def test_optimistic_concurrency_raises_conflict(self, service, sample_data):
        from datetime import datetime
        from exceptions import ConflictError

        equip = service.create_equipment(sample_data)
        stale_ts = datetime(2000, 1, 1)
        with pytest.raises(ConflictError):
            service.unassign_equipment(equip.id, expected_updated_at=stale_ts)


class TestChangeStatus:
    def test_changes_status_successfully(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        result = service.change_status(equip.id, "Under Repair")
        assert result.status == "Under Repair"

    def test_records_status_change_history(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.change_status(equip.id, "Under Repair")
        history = EquipmentSnapshot.query.filter_by(
            equipment_id=equip.id, change_type="StatusChange"
        ).all()
        assert len(history) == 1
        assert history[0].status == "Under Repair"
        assert "Available" in history[0].description
        assert "Under Repair" in history[0].description

    def test_retiring_clears_assignee(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        service.assign_equipment(equip.id, "John Doe")
        result = service.change_status(equip.id, "Retired")
        assert result.status == "Retired"
        assert result.assignee is None

    def test_retiring_without_assignee_succeeds(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        result = service.change_status(equip.id, "Retired")
        assert result.status == "Retired"
        assert result.assignee is None

    def test_rejects_invalid_status(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        with pytest.raises(ValueError, match="Invalid status"):
            service.change_status(equip.id, "Broken")

    def test_raises_for_nonexistent_equipment(self, service):
        with pytest.raises(ValueError, match="Equipment not found"):
            service.change_status(9999, "Available")

    def test_optimistic_concurrency_passes(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        ts = equip.updated_at
        result = service.change_status(equip.id, "Under Repair", expected_updated_at=ts)
        assert result.status == "Under Repair"

    def test_optimistic_concurrency_raises_conflict(self, service, sample_data):
        from datetime import datetime
        from exceptions import ConflictError

        equip = service.create_equipment(sample_data)
        stale_ts = datetime(2000, 1, 1)
        with pytest.raises(ConflictError):
            service.change_status(equip.id, "Under Repair", expected_updated_at=stale_ts)

    def test_all_valid_statuses_accepted(self, service, sample_data):
        for status in ["Available", "Assigned", "Under Repair", "Retired"]:
            data = dict(sample_data, asset_tag=f"AT-{status}", serial_number=f"SN-{status}")
            equip = service.create_equipment(data)
            result = service.change_status(equip.id, status)
            assert result.status == status


class TestListEquipment:
    @pytest.fixture(autouse=True)
    def setup_categories(self, app):
        """Seed categories used by list tests."""
        with app.app_context():
            for name in ["Laptops", "Monitors", "Servers"]:
                if not Category.query.filter_by(name=name).first():
                    db.session.add(Category(name=name))
            db.session.commit()

    def _create_items(self, service):
        """Create a few equipment records for testing."""
        base = {
            "manufacturer": "Dell",
            "model": "XPS 15",
            "purchase_date": date(2024, 1, 1),
            "purchase_cost": 1500.00,
            "warranty_expiration_date": date(2027, 1, 1),
        }
        items = [
            {"asset_tag": "AT-100", "name": "Alpha Laptop", "category": "Laptops",
             "serial_number": "SN-100", "location": "Building A", "notes": "Has docking station"},
            {"asset_tag": "AT-200", "name": "Beta Monitor", "category": "Monitors",
             "serial_number": "SN-200", "location": "Building B", "notes": None},
            {"asset_tag": "AT-300", "name": "Gamma Server", "category": "Servers",
             "serial_number": "SN-300", "location": None, "notes": "Rack mounted"},
        ]
        created = []
        for item in items:
            data = {**base, **item}
            created.append(service.create_equipment(data))
        return created

    def test_list_all_equipment(self, service):
        self._create_items(service)
        result = service.list_equipment()
        assert result.total == 3
        assert len(result.items) == 3

    def test_list_returns_empty_when_no_records(self, service):
        result = service.list_equipment()
        assert result.items == []
        assert result.total == 0

    def test_search_by_name(self, service):
        self._create_items(service)
        result = service.list_equipment(search="Alpha")
        assert len(result.items) == 1
        assert result.items[0].name == "Alpha Laptop"

    def test_search_by_asset_tag(self, service):
        self._create_items(service)
        result = service.list_equipment(search="AT-200")
        assert len(result.items) == 1
        assert result.items[0].asset_tag == "AT-200"

    def test_search_by_serial_number(self, service):
        self._create_items(service)
        result = service.list_equipment(search="SN-300")
        assert len(result.items) == 1
        assert result.items[0].serial_number == "SN-300"

    def test_search_by_category(self, service):
        self._create_items(service)
        result = service.list_equipment(search="Monitors")
        assert len(result.items) == 1
        assert result.items[0].category == "Monitors"

    def test_search_by_location(self, service):
        self._create_items(service)
        result = service.list_equipment(search="Building A")
        assert len(result.items) == 1
        assert result.items[0].location == "Building A"

    def test_search_by_notes(self, service):
        self._create_items(service)
        result = service.list_equipment(search="docking")
        assert len(result.items) == 1
        assert "docking" in result.items[0].notes.lower()

    def test_search_by_assignee(self, service):
        items = self._create_items(service)
        service.assign_equipment(items[0].id, "John Doe")
        result = service.list_equipment(search="John")
        assert len(result.items) == 1
        assert result.items[0].assignee == "John Doe"

    def test_search_is_case_insensitive(self, service):
        self._create_items(service)
        result = service.list_equipment(search="alpha")
        assert len(result.items) == 1
        assert result.items[0].name == "Alpha Laptop"

    def test_search_no_match_returns_empty(self, service):
        self._create_items(service)
        result = service.list_equipment(search="NonExistentThing")
        assert result.items == []

    def test_sort_by_name_ascending(self, service):
        self._create_items(service)
        result = service.list_equipment(sort_by="name", sort_order="asc")
        names = [r.name for r in result.items]
        assert names == sorted(names)

    def test_sort_by_name_descending(self, service):
        self._create_items(service)
        result = service.list_equipment(sort_by="name", sort_order="desc")
        names = [r.name for r in result.items]
        assert names == sorted(names, reverse=True)

    def test_sort_by_asset_tag(self, service):
        self._create_items(service)
        result = service.list_equipment(sort_by="asset_tag", sort_order="asc")
        tags = [r.asset_tag for r in result.items]
        assert tags == sorted(tags)

    def test_sort_by_invalid_column_ignored(self, service):
        self._create_items(service)
        result = service.list_equipment(sort_by="nonexistent_field")
        assert len(result.items) == 3

    def test_search_and_sort_combined(self, service):
        self._create_items(service)
        # Search for items with "Laptop" or "Server" won't both match,
        # but searching for a common manufacturer should return all, then sort
        result = service.list_equipment(search="SN-", sort_by="asset_tag", sort_order="desc")
        assert len(result.items) == 3
        tags = [r.asset_tag for r in result.items]
        assert tags == sorted(tags, reverse=True)

    def test_sort_defaults_to_ascending(self, service):
        self._create_items(service)
        result = service.list_equipment(sort_by="name")
        names = [r.name for r in result.items]
        assert names == sorted(names)

    def test_pagination_returns_correct_page(self, service):
        self._create_items(service)
        result = service.list_equipment(per_page=2, page=1)
        assert len(result.items) == 2
        assert result.total == 3
        assert result.pages == 2

    def test_pagination_second_page(self, service):
        self._create_items(service)
        result = service.list_equipment(per_page=2, page=2)
        assert len(result.items) == 1

    def test_pagination_out_of_range_returns_empty(self, service):
        self._create_items(service)
        result = service.list_equipment(per_page=20, page=99)
        assert result.items == []


class TestLookupByAssetTag:
    def test_returns_equipment_for_existing_tag(self, service, sample_data):
        equip = service.create_equipment(sample_data)
        result = service.lookup_by_asset_tag("AT-001")
        assert result is not None
        assert result.id == equip.id
        assert result.asset_tag == "AT-001"

    def test_returns_none_for_nonexistent_tag(self, service):
        result = service.lookup_by_asset_tag("DOES-NOT-EXIST")
        assert result is None

    def test_exact_match_only(self, service, sample_data):
        service.create_equipment(sample_data)
        # Partial match should not return anything
        assert service.lookup_by_asset_tag("AT-00") is None
        assert service.lookup_by_asset_tag("AT-0011") is None
        assert service.lookup_by_asset_tag("at-001") is None  # case-sensitive


class TestGetDashboardSummary:
    @pytest.fixture(autouse=True)
    def setup_categories(self, app):
        with app.app_context():
            for name in ["Laptops", "Monitors", "Servers"]:
                if not Category.query.filter_by(name=name).first():
                    db.session.add(Category(name=name))
            db.session.commit()

    def _make_data(self, asset_tag, serial_number, category="Laptops"):
        return {
            "asset_tag": asset_tag,
            "name": f"Item {asset_tag}",
            "category": category,
            "manufacturer": "Dell",
            "model": "XPS 15",
            "serial_number": serial_number,
            "purchase_date": date(2024, 1, 1),
            "purchase_cost": 1000.00,
            "warranty_expiration_date": date(2027, 1, 1),
        }

    def test_empty_database_returns_empty_dicts(self, service):
        summary = service.get_dashboard_summary()
        assert summary["by_status"] == {}
        assert summary["by_category"] == {}
        assert summary["total_count"] == 0
        assert summary["total_value"] == 0.0

    def test_counts_by_status(self, service):
        service.create_equipment(self._make_data("A1", "S1"))
        service.create_equipment(self._make_data("A2", "S2"))
        e3 = service.create_equipment(self._make_data("A3", "S3"))
        service.change_status(e3.id, "Under Repair")

        summary = service.get_dashboard_summary()
        assert summary["by_status"]["Available"] == 2
        assert summary["by_status"]["Under Repair"] == 1

    def test_counts_by_category(self, service):
        service.create_equipment(self._make_data("A1", "S1", "Laptops"))
        service.create_equipment(self._make_data("A2", "S2", "Laptops"))
        service.create_equipment(self._make_data("A3", "S3", "Monitors"))

        summary = service.get_dashboard_summary()
        assert summary["by_category"]["Laptops"] == 2
        assert summary["by_category"]["Monitors"] == 1

    def test_summary_reflects_all_statuses(self, service):
        e1 = service.create_equipment(self._make_data("A1", "S1"))
        e2 = service.create_equipment(self._make_data("A2", "S2"))
        e3 = service.create_equipment(self._make_data("A3", "S3"))
        e4 = service.create_equipment(self._make_data("A4", "S4"))
        service.assign_equipment(e2.id, "Alice")
        service.change_status(e3.id, "Under Repair")
        service.change_status(e4.id, "Retired")

        summary = service.get_dashboard_summary()
        assert summary["by_status"] == {
            "Available": 1,
            "Assigned": 1,
            "Under Repair": 1,
            "Retired": 1,
        }
