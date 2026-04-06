from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from models import User


class UserService:

    VALID_ROLES = {"admin", "viewer"}

    def create_user(self, username: str, password: str, role: str = "viewer") -> User:
        """Create a new user with a hashed password. Defaults to Viewer role. Rejects duplicate usernames."""
        existing = User.query.filter_by(username=username).first()
        if existing:
            raise ValueError(f"Username '{username}' already exists")

        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(sorted(self.VALID_ROLES))}")

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def authenticate(self, username: str, password: str) -> User | None:
        """Verify credentials. Returns the User if valid, None otherwise."""
        user = User.query.filter_by(username=username).first()
        if user is None:
            return None
        if not check_password_hash(user.password_hash, password):
            return None
        return user

    def delete_user(self, user_id: int) -> None:
        """Delete a user account."""
        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError(f"User with id {user_id} not found")
        db.session.delete(user)
        db.session.commit()

    def change_role(self, user_id: int, new_role: str) -> User:
        """Change a user's role. new_role must be 'admin' or 'viewer'."""
        if new_role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role '{new_role}'. Must be one of: {', '.join(sorted(self.VALID_ROLES))}")

        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError(f"User with id {user_id} not found")

        user.role = new_role
        db.session.commit()
        return user

    def list_users(self) -> list[User]:
        """Return all user accounts."""
        return User.query.all()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieve a user by ID. Used by Flask-Login's user_loader."""
        return db.session.get(User, user_id)

    def change_password(self, user_id: int, current_password: str, new_password: str) -> User:
        """Change a user's password after verifying the current one."""
        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError(f"User with id {user_id} not found")
        if not check_password_hash(user.password_hash, current_password):
            raise ValueError("Current password is incorrect")
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        return user
