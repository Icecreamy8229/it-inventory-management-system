from models import Equipment, Category


def validate_equipment_data(data: dict, is_update: bool = False, equipment_id: int = None) -> list[str]:
    """
    Validate equipment form data. Returns a list of error messages.
    Checks required fields, asset tag uniqueness, serial number uniqueness,
    and that the category value exists in the Category table.
    Location and Notes are optional.
    """
    errors = []

    required_fields = [
        "asset_tag",
        "name",
    ]

    # Check required fields
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(f"{field} is required")

    # If there are missing required fields, return early before uniqueness/category checks
    if errors:
        return errors

    # Check asset_tag uniqueness
    asset_tag = data.get("asset_tag")
    if asset_tag:
        query = Equipment.query.filter_by(asset_tag=asset_tag)
        if is_update and equipment_id is not None:
            query = query.filter(Equipment.id != equipment_id)
        if query.first() is not None:
            errors.append("asset_tag already exists")

    # Check serial_number uniqueness
    serial_number = data.get("serial_number")
    if serial_number:
        query = Equipment.query.filter_by(serial_number=serial_number)
        if is_update and equipment_id is not None:
            query = query.filter(Equipment.id != equipment_id)
        if query.first() is not None:
            errors.append("serial_number already exists")

    # Check category exists in Category table
    category = data.get("category")
    if category:
        existing_category = Category.query.filter_by(name=category).first()
        if existing_category is None:
            errors.append(f"category '{category}' does not exist")

    return errors
