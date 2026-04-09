import os
import uuid
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from models import Equipment, EquipmentHistory, EquipmentSnapshot
from services.validation import validate_equipment_data
from exceptions import ConflictError

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


class EquipmentService:

    VALID_STATUSES = {"Available", "Assigned", "Under Repair", "Retired"}

    @staticmethod
    def _create_snapshot(equipment, change_type, description, username=None):
        """Create a point-in-time snapshot of the equipment's current state."""
        return EquipmentSnapshot(
            equipment_id=equipment.id,
            change_type=change_type,
            description=description,
            changed_by=username,
            asset_tag=equipment.asset_tag,
            name=equipment.name,
            category=equipment.category,
            manufacturer=equipment.manufacturer,
            model=equipment.model,
            serial_number=equipment.serial_number,
            purchase_date=equipment.purchase_date,
            purchase_cost=equipment.purchase_cost,
            warranty_expiration_date=equipment.warranty_expiration_date,
            status=equipment.status,
            assignee=equipment.assignee,
            location=equipment.location,
            notes=equipment.notes,
            image_filename=equipment.image_filename,
        )

    def create_equipment(self, data: dict, image_file=None, username: str = None) -> Equipment:
        """Validate and create a new equipment record with user-provided asset tag."""
        errors = validate_equipment_data(data)
        if image_file:
            errors = errors or []
            errors.extend(self._validate_image(image_file))
        if errors:
            raise ValueError(errors)

        image_filename = None
        if image_file and image_file.filename:
            image_filename = self._save_image(image_file)

        equipment = Equipment(
            asset_tag=data["asset_tag"],
            name=data["name"],
            category=data.get("category"),
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            serial_number=data.get("serial_number"),
            purchase_date=data.get("purchase_date"),
            purchase_cost=data.get("purchase_cost"),
            warranty_expiration_date=data.get("warranty_expiration_date"),
            status="Available",
            location=data.get("location"),
            notes=data.get("notes"),
            image_filename=image_filename,
        )
        db.session.add(equipment)
        db.session.flush()

        history = EquipmentHistory(
            equipment_id=equipment.id,
            change_type="Created",
            description="Equipment record created",
            changed_by=username,
        )
        db.session.add(history)
        db.session.add(self._create_snapshot(equipment, "Created", "Equipment record created", username))
        db.session.commit()
        return equipment

    def update_equipment(self, equipment_id: int, data: dict, image_file=None, remove_image: bool = False, expected_updated_at: datetime = None, username: str = None) -> Equipment:
        """Validate and update an equipment record, recording history."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")

        if expected_updated_at is not None and equipment.updated_at != expected_updated_at:
            raise ConflictError("This record was modified by another user. Please refresh and try again.")

        errors = validate_equipment_data(data, is_update=True, equipment_id=equipment_id)
        if image_file:
            errors = errors or []
            errors.extend(self._validate_image(image_file))
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

        # Handle image upload / removal
        if remove_image and equipment.image_filename:
            self._delete_image(equipment.image_filename)
            changed_fields.append("image")
            old_values["image"] = equipment.image_filename
            new_values["image"] = None
            equipment.image_filename = None
        elif image_file and image_file.filename:
            old_image = equipment.image_filename
            new_filename = self._save_image(image_file)
            if old_image:
                self._delete_image(old_image)
            equipment.image_filename = new_filename
            changed_fields.append("image")
            old_values["image"] = old_image
            new_values["image"] = new_filename

        if changed_fields:
            description = "Updated fields: " + ", ".join(changed_fields)
            previous_value = "; ".join(f"{f}: {old_values[f]}" for f in changed_fields)
            new_value = "; ".join(f"{f}: {new_values[f]}" for f in changed_fields)
            history = EquipmentHistory(
                equipment_id=equipment.id, change_type="Updated",
                description=description, previous_value=previous_value, new_value=new_value,
                changed_by=username,
            )
            db.session.add(history)
            db.session.add(self._create_snapshot(equipment, "Updated", description, username))

        db.session.commit()
        return equipment

    def assign_equipment(self, equipment_id: int, assignee: str, expected_updated_at: datetime = None, username: str = None) -> Equipment:
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
        description = f"Assigned to {assignee}"
        history = EquipmentHistory(
            equipment_id=equipment.id, change_type="Assignment",
            description=description, previous_value=previous_assignee, new_value=assignee,
            changed_by=username,
        )
        db.session.add(history)
        db.session.add(self._create_snapshot(equipment, "Assignment", description, username))
        db.session.commit()
        return equipment

    def unassign_equipment(self, equipment_id: int, expected_updated_at: datetime = None, username: str = None) -> Equipment:
        """Unassign equipment and set status to Available."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        if expected_updated_at is not None and equipment.updated_at != expected_updated_at:
            raise ConflictError("This record was modified by another user. Please refresh and try again.")

        previous_assignee = equipment.assignee
        equipment.assignee = None
        equipment.status = "Available"
        description = f"Unassigned from {previous_assignee}"
        history = EquipmentHistory(
            equipment_id=equipment.id, change_type="Unassignment",
            description=description, previous_value=previous_assignee, new_value=None,
            changed_by=username,
        )
        db.session.add(history)
        db.session.add(self._create_snapshot(equipment, "Unassignment", description, username))
        db.session.commit()
        return equipment

    def change_status(self, equipment_id: int, new_status: str, expected_updated_at: datetime = None, username: str = None) -> Equipment:
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
        description = f"Status changed from {previous_status} to {new_status}"
        history = EquipmentHistory(
            equipment_id=equipment.id, change_type="StatusChange",
            description=description,
            previous_value=previous_status, new_value=new_status,
            changed_by=username,
        )
        db.session.add(history)
        db.session.add(self._create_snapshot(equipment, "StatusChange", description, username))
        db.session.commit()
        return equipment

    def list_equipment(self, search: str = None, sort_by: str = None, sort_order: str = "asc", filter_type: str = None, page: int = 1, per_page: int = 20):
        """List equipment with optional search, sorting, preset filters, and pagination.

        Returns a Flask-SQLAlchemy Pagination object with .items, .pages, .page, .total, etc.
        """
        from datetime import date, timedelta

        query = Equipment.query

        # Apply preset filters
        if filter_type:
            if filter_type == "warranty_expiring":
                today = date.today()
                query = query.filter(
                    Equipment.warranty_expiration_date.isnot(None),
                    Equipment.warranty_expiration_date >= today,
                    Equipment.warranty_expiration_date <= today + timedelta(days=90),
                )
            elif filter_type == "aging":
                cutoff = date.today() - timedelta(days=int(4 * 365.25))
                query = query.filter(
                    Equipment.purchase_date.isnot(None),
                    Equipment.purchase_date <= cutoff,
                )
            elif filter_type.startswith("status:"):
                query = query.filter(Equipment.status == filter_type.split(":", 1)[1])
            elif filter_type.startswith("category:"):
                query = query.filter(Equipment.category == filter_type.split(":", 1)[1])
            elif filter_type.startswith("assignee:"):
                query = query.filter(Equipment.assignee == filter_type.split(":", 1)[1])

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

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def lookup_by_asset_tag(self, asset_tag: str) -> Equipment | None:
        """Look up a single equipment record by exact asset tag match."""
        return Equipment.query.filter_by(asset_tag=asset_tag).first()

    def get_dashboard_summary(self) -> dict:
        """Return counts grouped by status, category, plus warranty alerts, asset value, age, and assignment density."""
        from datetime import date, timedelta

        equipment_list = Equipment.query.all()
        today = date.today()

        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        total_value = 0.0
        value_by_category: dict[str, float] = {}
        value_by_status: dict[str, float] = {}
        warranty_expiring: list[Equipment] = []
        aging_items: list[Equipment] = []
        by_assignee: dict[str, int] = {}
        age_by_category: dict[str, list[int]] = {}

        for item in equipment_list:
            # Status counts
            by_status[item.status] = by_status.get(item.status, 0) + 1

            # Category counts
            cat_key = item.category or "Uncategorized"
            by_category[cat_key] = by_category.get(cat_key, 0) + 1

            # Asset value
            cost = item.purchase_cost or 0
            total_value += cost
            value_by_category[cat_key] = value_by_category.get(cat_key, 0) + cost
            value_by_status[item.status] = value_by_status.get(item.status, 0) + cost

            # Warranty expiring within 90 days
            if item.warranty_expiration_date and today <= item.warranty_expiration_date <= today + timedelta(days=90):
                warranty_expiring.append(item)

            # Equipment age
            if item.purchase_date:
                age_days = (today - item.purchase_date).days
                age_years = age_days / 365.25
                if cat_key not in age_by_category:
                    age_by_category[cat_key] = []
                age_by_category[cat_key].append(age_days)
                if age_years >= 4:
                    aging_items.append(item)

            # Assignment density
            if item.assignee:
                by_assignee[item.assignee] = by_assignee.get(item.assignee, 0) + 1

        # Compute average age per category in years
        avg_age_by_category = {}
        for cat, ages in age_by_category.items():
            avg_days = sum(ages) / len(ages)
            avg_age_by_category[cat] = round(avg_days / 365.25, 1)

        # Sort warranty expiring by date
        warranty_expiring.sort(key=lambda e: e.warranty_expiration_date)

        # Sort assignees by count descending
        by_assignee = dict(sorted(by_assignee.items(), key=lambda x: x[1], reverse=True))

        return {
            "by_status": by_status,
            "by_category": by_category,
            "total_value": total_value,
            "value_by_category": value_by_category,
            "value_by_status": value_by_status,
            "warranty_expiring": warranty_expiring,
            "aging_items": aging_items,
            "avg_age_by_category": avg_age_by_category,
            "by_assignee": by_assignee,
            "total_count": len(equipment_list),
        }

    def get_equipment(self, equipment_id: int) -> Equipment:
        """Retrieve a single equipment record with full details."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        return equipment

    def get_snapshot(self, snapshot_id: int) -> EquipmentSnapshot:
        """Retrieve a single equipment snapshot."""
        snapshot = db.session.get(EquipmentSnapshot, snapshot_id)
        if snapshot is None:
            raise ValueError("Snapshot not found")
        return snapshot

    def delete_equipment(self, equipment_id: int) -> None:
        """Delete an equipment record."""
        equipment = db.session.get(Equipment, equipment_id)
        if equipment is None:
            raise ValueError("Equipment not found")
        if equipment.image_filename:
            self._delete_image(equipment.image_filename)
        db.session.delete(equipment)
        db.session.commit()

    # ----- Image helpers -----

    @staticmethod
    def _validate_image(image_file) -> list[str]:
        """Return a list of validation errors for the uploaded image."""
        errors = []
        if image_file and image_file.filename:
            ext = image_file.filename.rsplit(".", 1)[-1].lower() if "." in image_file.filename else ""
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                errors.append(f"Image must be one of: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}")
            image_file.seek(0, 2)
            size = image_file.tell()
            image_file.seek(0)
            if size > MAX_IMAGE_SIZE:
                errors.append("Image must be smaller than 5 MB")
        return errors

    @staticmethod
    def _save_image(image_file) -> str:
        """Save an image file and return the stored filename."""
        upload_path = current_app.config["UPLOAD_PATH"]
        ext = image_file.filename.rsplit(".", 1)[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        image_file.save(os.path.join(upload_path, filename))
        return filename

    @staticmethod
    def _delete_image(filename: str) -> None:
        """Delete an image file from the upload directory."""
        upload_path = current_app.config["UPLOAD_PATH"]
        filepath = os.path.join(upload_path, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
