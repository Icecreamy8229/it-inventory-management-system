from datetime import datetime

from app import db
from models import Equipment, EquipmentHistory
from services.validation import validate_equipment_data
from exceptions import ConflictError


class EquipmentService:

    VALID_STATUSES = {"Available", "Assigned", "Under Repair", "Retired"}

    def create_equipment(self, data: dict) -> Equipment:
        """Validate and create a new equipment record with user-provided asset tag."""
        errors = validate_equipment_data(data)
        if errors:
            raise ValueError(errors)

        equipment = Equipment(
            asset_tag=data["asset_tag"],
            name=data["name"],
            category=data["category"],
            manufacturer=data["manufacturer"],
            model=data["model"],
            serial_number=data["serial_number"],
            purchase_date=data.get("purchase_date"),
            purchase_cost=data["purchase_cost"],
            warranty_expiration_date=data.get("warranty_expiration_date"),
            status="Available",
            location=data.get("location"),
            notes=data.get("notes"),
        )
        db.session.add(equipment)
        db.session.flush()

        history = EquipmentHistory(
            equipment_id=equipment.id,
            change_type="Created",
            description="Equipment record created",
        )
        db.session.add(history)
        db.session.commit()
        return equipment

    def update_equipment(self, equipment_id: int, data: dict, expected_updated_at: datetime = None) -> Equipment:
        """Validate and update an equipment record, recording history."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")

        if expected_updated_at is not None and equipment.updated_at != expected_updated_at:
            raise ConflictError("This record was modified by another user. Please refresh and try again.")

        errors = validate_equipment_data(data, is_update=True, equipment_id=equipment_id)
        if errors:
            raise ValueError(errors)

        updatable_fields = [
            "asset_tag", "name", "category", "manufacturer", "model",
            "serial_number", "purchase_date", "purchase_cost",
            "warranty_expiration_date", "location", "notes",
        ]
        changed_fields = []
        old_values = {}
        new_values = {}
        for field in updatable_fields:
            if field in data:
                old_val = getattr(equipment, field)
                new_val = data[field]
                if old_val != new_val:
                    changed_fields.append(field)
                    old_values[field] = str(old_val) if old_val is not None else None
                    new_values[field] = str(new_val) if new_val is not None else None

        for field in updatable_fields:
            if field in data:
                setattr(equipment, field, data[field])

        if changed_fields:
            description = "Updated fields: " + ", ".join(changed_fields)
            previous_value = "; ".join(f"{f}: {old_values[f]}" for f in changed_fields)
            new_value = "; ".join(f"{f}: {new_values[f]}" for f in changed_fields)
            history = EquipmentHistory(
                equipment_id=equipment.id, change_type="Updated",
                description=description, previous_value=previous_value, new_value=new_value,
            )
            db.session.add(history)

        db.session.commit()
        return equipment

    def assign_equipment(self, equipment_id: int, assignee: str, expected_updated_at: datetime = None) -> Equipment:
        """Assign equipment to an employee/department. Rejects if Retired or Under Repair."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        if expected_updated_at is not None and equipment.updated_at != expected_updated_at:
            raise ConflictError("This record was modified by another user. Please refresh and try again.")
        if equipment.status in ("Retired", "Under Repair"):
            raise ValueError("Equipment is not available for assignment")

        previous_assignee = equipment.assignee
        equipment.assignee = assignee
        equipment.status = "Assigned"
        history = EquipmentHistory(
            equipment_id=equipment.id, change_type="Assignment",
            description=f"Assigned to {assignee}", previous_value=previous_assignee, new_value=assignee,
        )
        db.session.add(history)
        db.session.commit()
        return equipment

    def unassign_equipment(self, equipment_id: int, expected_updated_at: datetime = None) -> Equipment:
        """Unassign equipment and set status to Available."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        if expected_updated_at is not None and equipment.updated_at != expected_updated_at:
            raise ConflictError("This record was modified by another user. Please refresh and try again.")

        previous_assignee = equipment.assignee
        equipment.assignee = None
        equipment.status = "Available"
        history = EquipmentHistory(
            equipment_id=equipment.id, change_type="Unassignment",
            description=f"Unassigned from {previous_assignee}", previous_value=previous_assignee, new_value=None,
        )
        db.session.add(history)
        db.session.commit()
        return equipment

    def change_status(self, equipment_id: int, new_status: str, expected_updated_at: datetime = None) -> Equipment:
        """Change equipment status, enforcing transition rules."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        if expected_updated_at is not None and equipment.updated_at != expected_updated_at:
            raise ConflictError("This record was modified by another user. Please refresh and try again.")
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(self.VALID_STATUSES))}")

        previous_status = equipment.status
        if new_status == "Retired":
            equipment.assignee = None
        equipment.status = new_status
        history = EquipmentHistory(
            equipment_id=equipment.id, change_type="StatusChange",
            description=f"Status changed from {previous_status} to {new_status}",
            previous_value=previous_status, new_value=new_status,
        )
        db.session.add(history)
        db.session.commit()
        return equipment

    def list_equipment(self, search: str = None, sort_by: str = None, sort_order: str = "asc") -> list:
        """List equipment with optional search and sorting."""
        query = Equipment.query

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    Equipment.asset_tag.ilike(pattern),
                    Equipment.name.ilike(pattern),
                    Equipment.serial_number.ilike(pattern),
                    Equipment.category.ilike(pattern),
                    Equipment.assignee.ilike(pattern),
                    Equipment.location.ilike(pattern),
                    Equipment.notes.ilike(pattern),
                )
            )

        valid_columns = {
            "asset_tag", "name", "serial_number", "category", "manufacturer",
            "model", "purchase_date", "purchase_cost", "warranty_expiration_date",
            "status", "assignee", "location", "notes", "created_at", "updated_at",
        }
        if sort_by and sort_by in valid_columns:
            column = getattr(Equipment, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())

        return query.all()

    def lookup_by_asset_tag(self, asset_tag: str) -> Equipment | None:
        """Look up a single equipment record by exact asset tag match."""
        return Equipment.query.filter_by(asset_tag=asset_tag).first()

    def get_dashboard_summary(self) -> dict:
        """Return counts grouped by status and category."""
        equipment_list = Equipment.query.all()
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for item in equipment_list:
            by_status[item.status] = by_status.get(item.status, 0) + 1
            by_category[item.category] = by_category.get(item.category, 0) + 1
        return {"by_status": by_status, "by_category": by_category}

    def get_equipment(self, equipment_id: int) -> Equipment:
        """Retrieve a single equipment record with full details."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        return equipment

    def delete_equipment(self, equipment_id: int) -> None:
        """Delete an equipment record."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        db.session.delete(equipment)
        db.session.commit()
