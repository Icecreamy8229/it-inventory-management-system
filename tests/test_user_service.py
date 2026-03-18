import pytest
from werkzeug.security import check_password_hash

from app import create_app, db
from models import User
from services.user_service import UserService


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
    """Return a UserService instance within app context."""
    with app.app_context():
        yield UserService()


class TestCreateUser:
    def test_creates_user_with_defaults(self, service):
        user = service.create_user("alice", "secret123")
        assert user.username == "alice"
        assert user.role == "viewer"
        assert user.id is not None

    def test_password_is_hashed(self, service):
        user = service.create_user("alice", "secret123")
        assert user.password_hash != "secret123"
        assert check_password_hash(user.password_hash, "secret123")

    def test_creates_user_with_admin_role(self, service):
        user = service.create_user("admin_user", "pass", role="admin")
        assert user.role == "admin"

    def test_rejects_duplicate_username(self, service):
        service.create_user("alice", "pass1")
        with pytest.raises(ValueError, match="already exists"):
            service.create_user("alice", "pass2")

    def test_rejects_invalid_role(self, service):
        with pytest.raises(ValueError, match="Invalid role"):
            service.create_user("bob", "pass", role="superadmin")


class TestAuthenticate:
    def test_valid_credentials(self, service):
        service.create_user("alice", "secret123")
        user = service.authenticate("alice", "secret123")
        assert user is not None
        assert user.username == "alice"

    def test_wrong_password(self, service):
        service.create_user("alice", "secret123")
        assert service.authenticate("alice", "wrongpass") is None

    def test_nonexistent_user(self, service):
        assert service.authenticate("nobody", "pass") is None


class TestDeleteUser:
    def test_deletes_existing_user(self, service):
        user = service.create_user("alice", "pass")
        service.delete_user(user.id)
        assert service.get_user_by_id(user.id) is None

    def test_raises_for_nonexistent_user(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.delete_user(9999)


class TestChangeRole:
    def test_changes_viewer_to_admin(self, service):
        user = service.create_user("alice", "pass")
        updated = service.change_role(user.id, "admin")
        assert updated.role == "admin"

    def test_changes_admin_to_viewer(self, service):
        user = service.create_user("alice", "pass", role="admin")
        updated = service.change_role(user.id, "viewer")
        assert updated.role == "viewer"

    def test_rejects_invalid_role(self, service):
        user = service.create_user("alice", "pass")
        with pytest.raises(ValueError, match="Invalid role"):
            service.change_role(user.id, "superadmin")

    def test_raises_for_nonexistent_user(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.change_role(9999, "admin")


class TestListUsers:
    def test_empty_initially(self, service):
        assert service.list_users() == []

    def test_returns_all_users(self, service):
        service.create_user("alice", "pass1")
        service.create_user("bob", "pass2")
        users = service.list_users()
        usernames = [u.username for u in users]
        assert "alice" in usernames
        assert "bob" in usernames
        assert len(users) == 2


class TestGetUserById:
    def test_returns_existing_user(self, service):
        user = service.create_user("alice", "pass")
        found = service.get_user_by_id(user.id)
        assert found is not None
        assert found.username == "alice"

    def test_returns_none_for_nonexistent(self, service):
        assert service.get_user_by_id(9999) is None
