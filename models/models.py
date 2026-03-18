from datetime import datetime

from flask_login import UserMixin

from app import db


class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    manufacturer = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Float, nullable=False)
    warranty_expiration_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Available")
    assignee = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history_entries = db.relationship(
        "EquipmentHistory", backref="equipment", cascade="all, delete-orphan"
    )


class EquipmentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(
        db.Integer, db.ForeignKey("equipment.id"), nullable=False
    )
    change_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    change_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    previous_value = db.Column(db.String(200), nullable=True)
    new_value = db.Column(db.String(200), nullable=True)


class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    app_title = db.Column(db.String(200), nullable=False)
    logo_path = db.Column(db.String(500), nullable=True)
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
