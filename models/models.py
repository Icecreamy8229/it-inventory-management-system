from datetime import datetime
import json

from flask_login import UserMixin

from app import db


class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    manufacturer = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    serial_number = db.Column(db.String(100), unique=True, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Float, nullable=True)
    warranty_expiration_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Available")
    assignee = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    # Legacy column kept for migration; new images go to EquipmentImage table
    image_filename = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship(
        "EquipmentImage", backref="equipment", cascade="all, delete-orphan",
        order_by="EquipmentImage.position"
    )
    snapshots = db.relationship(
        "EquipmentSnapshot", backref="equipment", cascade="all, delete-orphan",
        order_by="EquipmentSnapshot.snapshot_date.desc()"
    )

    MAX_IMAGES = 5


class EquipmentImage(db.Model):
    """Individual image file associated with a piece of equipment."""
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(
        db.Integer, db.ForeignKey("equipment.id"), nullable=False
    )
    filename = db.Column(db.String(300), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EquipmentSnapshot(db.Model):
    """Point-in-time snapshot of all equipment attributes."""
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(
        db.Integer, db.ForeignKey("equipment.id"), nullable=False
    )
    snapshot_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    change_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    changed_by = db.Column(db.String(80), nullable=True)
    has_full_data = db.Column(db.Boolean, nullable=False, default=True)

    # Full copy of equipment fields at this point in time
    asset_tag = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    manufacturer = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    serial_number = db.Column(db.String(100), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Float, nullable=True)
    warranty_expiration_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=True)
    assignee = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    # JSON-encoded list of image filenames at this point in time
    image_filenames_json = db.Column(db.Text, nullable=True)

    @property
    def image_filenames(self):
        if not self.image_filenames_json:
            return []
        return json.loads(self.image_filenames_json)

    @image_filenames.setter
    def image_filenames(self, value):
        self.image_filenames_json = json.dumps(value) if value else None


class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    app_title = db.Column(db.String(200), nullable=False)
    logo_path = db.Column(db.String(500), nullable=True)
    site_url = db.Column(db.String(500), nullable=True)
    setup_complete = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
