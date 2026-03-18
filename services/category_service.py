from app import db
from models import Category, Equipment


class CategoryService:
    def list_categories(self) -> list[Category]:
        """Return all categories."""
        return Category.query.all()

    def add_category(self, name: str) -> Category:
        """Add a new category. Rejects duplicates."""
        existing = Category.query.filter_by(name=name).first()
        if existing:
            raise ValueError(f"Category '{name}' already exists")
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        return category

    def delete_category(self, category_id: int) -> None:
        """Delete a category. Rejects if any Equipment records reference it."""
        category = db.session.get(Category, category_id)
        if category is None:
            raise ValueError(f"Category with id {category_id} not found")
        in_use = Equipment.query.filter_by(category=category.name).first()
        if in_use:
            raise ValueError(
                f"Cannot delete category '{category.name}' because it is in use by equipment records"
            )
        db.session.delete(category)
        db.session.commit()

    def get_default_categories(self) -> list[str]:
        """Return the default category names."""
        return ["Laptops", "Monitors", "Peripherals", "Servers", "Networking"]
