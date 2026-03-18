import os
from datetime import datetime

from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from auth import admin_required
from exceptions import ConflictError
from services.category_service import CategoryService
from services.config_service import ConfigService
from services.equipment_service import EquipmentService
from services.user_service import UserService


def register_routes(app):
    """Register all route handlers on the Flask app."""

    # -------------------------------------------------------------------------
    # 8.1 - Setup wizard routes
    # -------------------------------------------------------------------------

    @app.route("/setup", methods=["GET"])
    def setup():
        config_service = ConfigService()
        if config_service.is_setup_complete():
            return redirect(url_for("dashboard"))
        category_service = CategoryService()
        default_categories = category_service.get_default_categories()
        return render_template("setup.html", default_categories=default_categories)

    @app.route("/setup", methods=["POST"])
    def setup_post():
        config_service_check = ConfigService()
        if config_service_check.is_setup_complete():
            return redirect(url_for("dashboard"))

        company_name = request.form.get("company_name", "").strip()
        app_title = request.form.get("app_title", "").strip()
        admin_username = request.form.get("admin_username", "").strip()
        admin_password = request.form.get("admin_password", "")
        admin_password_confirm = request.form.get("admin_password_confirm", "")
        logo_file = request.files.get("logo")

        # Collect categories from form
        categories = request.form.getlist("categories")

        errors = []
        if not company_name:
            errors.append("Company name is required.")
        if not app_title:
            errors.append("Application title is required.")
        if not admin_username:
            errors.append("Admin username is required.")
        if not admin_password:
            errors.append("Admin password is required.")
        if admin_password != admin_password_confirm:
            errors.append("Passwords do not match.")

        if errors:
            category_service = CategoryService()
            default_categories = category_service.get_default_categories()
            return render_template(
                "setup.html",
                default_categories=default_categories,
                errors=errors,
                company_name=company_name,
                app_title=app_title,
                admin_username=admin_username,
            )

        config_service = ConfigService()
        try:
            config_service.save_setup(
                company_name=company_name,
                app_title=app_title,
                logo_file=logo_file if logo_file and logo_file.filename else None,
                categories=categories if categories else None,
                admin_username=admin_username,
                admin_password=admin_password,
            )
        except ValueError as e:
            category_service = CategoryService()
            default_categories = category_service.get_default_categories()
            return render_template(
                "setup.html",
                default_categories=default_categories,
                errors=[str(e)],
                company_name=company_name,
                app_title=app_title,
                admin_username=admin_username,
            )

        flash("Setup complete! Welcome to your equipment inventory.", "success")
        return redirect(url_for("dashboard"))

    # -------------------------------------------------------------------------
    # 8.2 - Login / Logout routes
    # -------------------------------------------------------------------------

    @app.route("/login", methods=["GET"])
    def login():
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login_post():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_service = UserService()
        user = user_service.authenticate(username, password)
        if user is None:
            return render_template(
                "login.html",
                error="Invalid username or password",
                username=username,
            )

        login_user(user)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard"))

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # -------------------------------------------------------------------------
    # 8.3 - Dashboard route
    # -------------------------------------------------------------------------

    @app.route("/")
    @login_required
    def dashboard():
        equipment_service = EquipmentService()
        summary = equipment_service.get_dashboard_summary()
        return render_template(
            "dashboard.html",
            summary=summary,
        )

    # -------------------------------------------------------------------------
    # 8.4 - Equipment CRUD routes
    # -------------------------------------------------------------------------

    @app.route("/equipment")
    @login_required
    def equipment_list():
        search = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "")
        sort_order = request.args.get("sort_order", "asc")

        equipment_service = EquipmentService()
        items = equipment_service.list_equipment(
            search=search or None,
            sort_by=sort_by or None,
            sort_order=sort_order,
        )
        return render_template(
            "equipment_list.html",
            equipment=items,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    @app.route("/equipment/scan-lookup")
    @login_required
    def equipment_scan_lookup():
        asset_tag = request.args.get("asset_tag", "").strip()
        if not asset_tag:
            return redirect(url_for("equipment_list"))

        equipment_service = EquipmentService()
        item = equipment_service.lookup_by_asset_tag(asset_tag)
        if item:
            return redirect(url_for("equipment_detail", equipment_id=item.id))

        flash(f"No equipment found with asset tag '{asset_tag}'.", "warning")
        return redirect(url_for("equipment_list"))

    @app.route("/equipment/new")
    @login_required
    @admin_required
    def equipment_new():
        category_service = CategoryService()
        categories = category_service.list_categories()
        return render_template("equipment_form.html", categories=categories)

    @app.route("/equipment", methods=["POST"])
    @login_required
    @admin_required
    def equipment_create():
        data = _parse_equipment_form(request.form)

        equipment_service = EquipmentService()
        try:
            equipment = equipment_service.create_equipment(data)
        except ValueError as e:
            category_service = CategoryService()
            categories = category_service.list_categories()
            errors = e.args[0] if isinstance(e.args[0], list) else [str(e)]
            return render_template(
                "equipment_form.html",
                categories=categories,
                errors=errors,
                data=data,
            )

        flash("Equipment registered successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment.id))

    @app.route("/equipment/<int:equipment_id>")
    @login_required
    def equipment_detail(equipment_id):
        equipment_service = EquipmentService()
        try:
            item = equipment_service.get_equipment(equipment_id)
        except ValueError:
            flash("Equipment not found.", "error")
            return redirect(url_for("equipment_list"))

        return render_template("equipment_detail.html", equipment=item)

    @app.route("/equipment/<int:equipment_id>/edit")
    @login_required
    @admin_required
    def equipment_edit(equipment_id):
        equipment_service = EquipmentService()
        try:
            item = equipment_service.get_equipment(equipment_id)
        except ValueError:
            flash("Equipment not found.", "error")
            return redirect(url_for("equipment_list"))

        category_service = CategoryService()
        categories = category_service.list_categories()
        return render_template(
            "equipment_form.html",
            equipment=item,
            categories=categories,
        )

    @app.route("/equipment/<int:equipment_id>", methods=["POST"])
    @login_required
    @admin_required
    def equipment_update(equipment_id):
        data = _parse_equipment_form(request.form)
        expected_updated_at = _parse_expected_updated_at(request.form)

        equipment_service = EquipmentService()
        try:
            equipment = equipment_service.update_equipment(
                equipment_id, data, expected_updated_at=expected_updated_at
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template(
                "error.html",
                error=str(e),
                status_code=409,
            ), 409
        except ValueError as e:
            category_service = CategoryService()
            categories = category_service.list_categories()
            try:
                item = equipment_service.get_equipment(equipment_id)
            except ValueError:
                flash("Equipment not found.", "error")
                return redirect(url_for("equipment_list"))
            errors = e.args[0] if isinstance(e.args[0], list) else [str(e)]
            return render_template(
                "equipment_form.html",
                equipment=item,
                categories=categories,
                errors=errors,
                data=data,
            )

        flash("Equipment updated successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment.id))

    @app.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def equipment_delete(equipment_id):
        equipment_service = EquipmentService()
        try:
            equipment_service.delete_equipment(equipment_id)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_list"))

        flash("Equipment deleted successfully.", "success")
        return redirect(url_for("equipment_list"))

    # -------------------------------------------------------------------------
    # 8.5 - Assignment and status routes
    # -------------------------------------------------------------------------

    @app.route("/equipment/<int:equipment_id>/assign", methods=["POST"])
    @login_required
    @admin_required
    def equipment_assign(equipment_id):
        assignee = request.form.get("assignee", "").strip()
        expected_updated_at = _parse_expected_updated_at(request.form)

        if not assignee:
            flash("Assignee is required.", "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        equipment_service = EquipmentService()
        try:
            equipment_service.assign_equipment(
                equipment_id, assignee, expected_updated_at=expected_updated_at
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template(
                "error.html",
                error=str(e),
                status_code=409,
            ), 409
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        flash("Equipment assigned successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))

    @app.route("/equipment/<int:equipment_id>/unassign", methods=["POST"])
    @login_required
    @admin_required
    def equipment_unassign(equipment_id):
        expected_updated_at = _parse_expected_updated_at(request.form)

        equipment_service = EquipmentService()
        try:
            equipment_service.unassign_equipment(
                equipment_id, expected_updated_at=expected_updated_at
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template(
                "error.html",
                error=str(e),
                status_code=409,
            ), 409
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        flash("Equipment unassigned successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))

    @app.route("/equipment/<int:equipment_id>/status", methods=["POST"])
    @login_required
    @admin_required
    def equipment_status(equipment_id):
        new_status = request.form.get("status", "").strip()
        expected_updated_at = _parse_expected_updated_at(request.form)

        if not new_status:
            flash("Status is required.", "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        equipment_service = EquipmentService()
        try:
            equipment_service.change_status(
                equipment_id, new_status, expected_updated_at=expected_updated_at
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template(
                "error.html",
                error=str(e),
                status_code=409,
            ), 409
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        flash(f"Equipment status changed to '{new_status}'.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))

    # -------------------------------------------------------------------------
    # 8.6 - Settings and user management routes
    # -------------------------------------------------------------------------

    @app.route("/settings")
    @login_required
    @admin_required
    def settings():
        config_service = ConfigService()
        config = config_service.get_config()
        category_service = CategoryService()
        categories = category_service.list_categories()
        user_service = UserService()
        users = user_service.list_users()
        return render_template(
            "settings.html",
            config=config,
            categories=categories,
            users=users,
        )

    @app.route("/settings", methods=["POST"])
    @login_required
    @admin_required
    def settings_update():
        company_name = request.form.get("company_name", "").strip()
        app_title = request.form.get("app_title", "").strip()
        logo_file = request.files.get("logo")

        config_service = ConfigService()
        try:
            config_service.update_config(
                company_name=company_name or None,
                app_title=app_title or None,
                logo_file=logo_file if logo_file and logo_file.filename else None,
            )
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings"))

        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/categories", methods=["POST"])
    @login_required
    @admin_required
    def settings_add_category():
        name = request.form.get("name", "").strip()
        if not name:
            flash("Category name is required.", "error")
            return redirect(url_for("settings"))

        category_service = CategoryService()
        try:
            category_service.add_category(name)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings"))

        flash(f"Category '{name}' added.", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/categories/<int:category_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def settings_delete_category(category_id):
        category_service = CategoryService()
        try:
            category_service.delete_category(category_id)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings"))

        flash("Category deleted.", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/users")
    @login_required
    @admin_required
    def settings_users():
        user_service = UserService()
        users = user_service.list_users()
        return render_template("users.html", users=users)

    @app.route("/settings/users", methods=["POST"])
    @login_required
    @admin_required
    def settings_create_user():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        role = request.form.get("role", "viewer").strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("settings_users"))

        if password != password_confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("settings_users"))

        user_service = UserService()
        try:
            user_service.create_user(username, password, role=role)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings_users"))

        flash(f"User '{username}' created.", "success")
        return redirect(url_for("settings_users"))

    @app.route("/settings/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def settings_delete_user(user_id):
        user_service = UserService()
        try:
            user_service.delete_user(user_id)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings_users"))

        flash("User deleted.", "success")
        return redirect(url_for("settings_users"))

    @app.route("/settings/users/<int:user_id>/role", methods=["POST"])
    @login_required
    @admin_required
    def settings_change_role(user_id):
        new_role = request.form.get("role", "").strip()
        if not new_role:
            flash("Role is required.", "error")
            return redirect(url_for("settings_users"))

        user_service = UserService()
        try:
            user_service.change_role(user_id, new_role)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings_users"))

        flash("User role updated.", "success")
        return redirect(url_for("settings_users"))

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        upload_path = app.config["UPLOAD_PATH"]
        return send_from_directory(upload_path, filename)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_equipment_form(form) -> dict:
    """Extract equipment data from a form submission."""
    data = {
        "asset_tag": form.get("asset_tag", "").strip(),
        "name": form.get("name", "").strip(),
        "category": form.get("category", "").strip(),
        "manufacturer": form.get("manufacturer", "").strip(),
        "model": form.get("model", "").strip(),
        "serial_number": form.get("serial_number", "").strip(),
    }

    # Parse dates
    purchase_date_str = form.get("purchase_date", "").strip()
    if purchase_date_str:
        try:
            data["purchase_date"] = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
        except ValueError:
            data["purchase_date"] = purchase_date_str
    else:
        data["purchase_date"] = None

    warranty_date_str = form.get("warranty_expiration_date", "").strip()
    if warranty_date_str:
        try:
            data["warranty_expiration_date"] = datetime.strptime(warranty_date_str, "%Y-%m-%d").date()
        except ValueError:
            data["warranty_expiration_date"] = warranty_date_str
    else:
        data["warranty_expiration_date"] = None

    # Parse cost
    cost_str = form.get("purchase_cost", "").strip()
    if cost_str:
        try:
            data["purchase_cost"] = float(cost_str)
        except ValueError:
            data["purchase_cost"] = cost_str
    else:
        data["purchase_cost"] = ""

    # Optional fields
    location = form.get("location", "").strip()
    if location:
        data["location"] = location

    notes = form.get("notes", "").strip()
    if notes:
        data["notes"] = notes

    return data


def _parse_expected_updated_at(form) -> datetime | None:
    """Parse the expected_updated_at hidden field from a form."""
    value = form.get("expected_updated_at", "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
