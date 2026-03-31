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
from forms import (
    AddCategoryForm,
    AssignForm,
    ChangeRoleForm,
    ChangeStatusForm,
    CreateUserForm,
    DeleteCategoryForm,
    DeleteEquipmentForm,
    DeleteUserForm,
    EquipmentForm,
    LoginForm,
    SettingsForm,
    SetupForm,
    UnassignForm,
)
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
        form = SetupForm()
        category_service = CategoryService()
        default_categories = category_service.get_default_categories()
        return render_template("setup.html", form=form, default_categories=default_categories)

    @app.route("/setup", methods=["POST"])
    def setup_post():
        config_service_check = ConfigService()
        if config_service_check.is_setup_complete():
            return redirect(url_for("dashboard"))

        form = SetupForm()
        categories = request.form.getlist("categories")

        if not form.validate_on_submit():
            category_service = CategoryService()
            default_categories = category_service.get_default_categories()
            errors = []
            for field, field_errors in form.errors.items():
                for err in field_errors:
                    errors.append(err)
            return render_template(
                "setup.html",
                form=form,
                default_categories=default_categories,
                errors=errors,
            )

        logo_file = form.logo.data
        config_service = ConfigService()
        try:
            config_service.save_setup(
                company_name=form.company_name.data.strip(),
                app_title=form.app_title.data.strip(),
                logo_file=logo_file if logo_file and logo_file.filename else None,
                site_url=form.site_url.data.strip() if form.site_url.data else "",
                categories=categories if categories else None,
                admin_username=form.admin_username.data.strip(),
                admin_password=form.admin_password.data,
            )
        except ValueError as e:
            category_service = CategoryService()
            default_categories = category_service.get_default_categories()
            return render_template(
                "setup.html",
                form=form,
                default_categories=default_categories,
                errors=[str(e)],
            )

        flash("Setup complete! Welcome to your equipment inventory.", "success")
        return redirect(url_for("dashboard"))

    # -------------------------------------------------------------------------
    # 8.2 - Login / Logout routes
    # -------------------------------------------------------------------------

    @app.route("/login", methods=["GET"])
    def login():
        form = LoginForm()
        return render_template("login.html", form=form)

    @app.route("/login", methods=["POST"])
    def login_post():
        form = LoginForm()
        if not form.validate_on_submit():
            return render_template("login.html", form=form, error="Invalid input.")

        user_service = UserService()
        user = user_service.authenticate(form.username.data.strip(), form.password.data)
        if user is None:
            return render_template(
                "login.html",
                form=form,
                error="Invalid username or password",
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
        return render_template("dashboard.html", summary=summary)

    # -------------------------------------------------------------------------
    # 8.4 - Equipment CRUD routes
    # -------------------------------------------------------------------------

    @app.route("/equipment")
    @login_required
    def equipment_list():
        search = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "")
        sort_order = request.args.get("sort_order", "asc")
        filter_type = request.args.get("filter", "").strip()

        equipment_service = EquipmentService()
        items = equipment_service.list_equipment(
            search=search or None,
            sort_by=sort_by or None,
            sort_order=sort_order,
            filter_type=filter_type or None,
        )

        filter_label = ""
        if filter_type:
            if filter_type == "warranty_expiring":
                filter_label = "Warranties Expiring (next 90 days)"
            elif filter_type == "aging":
                filter_label = "Aging Equipment (4+ years)"
            elif filter_type.startswith("status:"):
                filter_label = f"Status: {filter_type.split(':', 1)[1]}"
            elif filter_type.startswith("category:"):
                filter_label = f"Category: {filter_type.split(':', 1)[1]}"
            elif filter_type.startswith("assignee:"):
                filter_label = f"Assignee: {filter_type.split(':', 1)[1]}"

        return render_template(
            "equipment_list.html",
            equipment=items,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_type=filter_type,
            filter_label=filter_label,
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

    @app.route("/equipment/export")
    @login_required
    def equipment_export():
        import io
        from openpyxl import Workbook
        from flask import send_file

        search = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "")
        sort_order = request.args.get("sort_order", "asc")
        filter_type = request.args.get("filter", "").strip()

        equipment_service = EquipmentService()
        items = equipment_service.list_equipment(
            search=search or None,
            sort_by=sort_by or None,
            sort_order=sort_order,
            filter_type=filter_type or None,
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Equipment"

        headers = [
            "Asset Tag", "Name", "Category", "Manufacturer", "Model",
            "Serial Number", "Status", "Assignee", "Location",
            "Purchase Date", "Purchase Cost", "Warranty Expiration", "Notes",
        ]
        ws.append(headers)

        for item in items:
            ws.append([
                item.asset_tag,
                item.name,
                item.category or "",
                item.manufacturer or "",
                item.model or "",
                item.serial_number or "",
                item.status,
                item.assignee or "",
                item.location or "",
                str(item.purchase_date) if item.purchase_date else "",
                item.purchase_cost if item.purchase_cost is not None else "",
                str(item.warranty_expiration_date) if item.warranty_expiration_date else "",
                item.notes or "",
            ])

        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="equipment_export.xlsx",
        )

    def _build_equipment_form(equipment=None):
        """Build an EquipmentForm with dynamic category choices."""
        form = EquipmentForm(obj=equipment)
        category_service = CategoryService()
        cats = category_service.list_categories()
        form.category.choices = [("", "Select a category")] + [(c.name, c.name) for c in cats]
        return form

    @app.route("/equipment/new")
    @login_required
    @admin_required
    def equipment_new():
        form = _build_equipment_form()
        return render_template("equipment_form.html", form=form)

    @app.route("/equipment", methods=["POST"])
    @login_required
    @admin_required
    def equipment_create():
        form = _build_equipment_form()

        if not form.validate_on_submit():
            errors = []
            for field, field_errors in form.errors.items():
                for err in field_errors:
                    errors.append(err)
            return render_template("equipment_form.html", form=form, errors=errors)

        data = _form_to_equipment_data(form)
        image_file = form.image.data if form.image.data and hasattr(form.image.data, "filename") and form.image.data.filename else None

        equipment_service = EquipmentService()
        try:
            equipment = equipment_service.create_equipment(data, image_file=image_file, username=current_user.username)
        except ValueError as e:
            errors = e.args[0] if isinstance(e.args[0], list) else [str(e)]
            return render_template("equipment_form.html", form=form, errors=errors)

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

        assign_form = AssignForm()
        unassign_form = UnassignForm()
        status_form = ChangeStatusForm()
        delete_form = DeleteEquipmentForm()
        if item.status:
            status_form.status.data = item.status

        return render_template(
            "equipment_detail.html",
            equipment=item,
            assign_form=assign_form,
            unassign_form=unassign_form,
            status_form=status_form,
            delete_form=delete_form,
        )

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

        form = _build_equipment_form(equipment=item)
        form.expected_updated_at.data = item.updated_at.isoformat()
        return render_template("equipment_form.html", form=form, equipment=item)

    @app.route("/equipment/<int:equipment_id>", methods=["POST"])
    @login_required
    @admin_required
    def equipment_update(equipment_id):
        form = _build_equipment_form()

        if not form.validate_on_submit():
            equipment_service = EquipmentService()
            try:
                item = equipment_service.get_equipment(equipment_id)
            except ValueError:
                flash("Equipment not found.", "error")
                return redirect(url_for("equipment_list"))
            errors = []
            for field, field_errors in form.errors.items():
                for err in field_errors:
                    errors.append(err)
            return render_template("equipment_form.html", form=form, equipment=item, errors=errors)

        data = _form_to_equipment_data(form)
        expected_updated_at = _parse_expected_updated_at(form.expected_updated_at.data)
        image_file = form.image.data if form.image.data and hasattr(form.image.data, "filename") and form.image.data.filename else None
        remove_image = form.remove_image.data

        equipment_service = EquipmentService()
        try:
            equipment = equipment_service.update_equipment(
                equipment_id, data, image_file=image_file, remove_image=remove_image,
                expected_updated_at=expected_updated_at, username=current_user.username,
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template("error.html", error=str(e), status_code=409), 409
        except ValueError as e:
            try:
                item = equipment_service.get_equipment(equipment_id)
            except ValueError:
                flash("Equipment not found.", "error")
                return redirect(url_for("equipment_list"))
            errors = e.args[0] if isinstance(e.args[0], list) else [str(e)]
            return render_template("equipment_form.html", form=form, equipment=item, errors=errors)

        flash("Equipment updated successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment.id))

    @app.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def equipment_delete(equipment_id):
        form = DeleteEquipmentForm()
        if not form.validate_on_submit():
            flash("Invalid request.", "error")
            return redirect(url_for("equipment_list"))

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
        form = AssignForm()
        if not form.validate_on_submit():
            flash("Assignee is required.", "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        expected_updated_at = _parse_expected_updated_at(form.expected_updated_at.data)
        equipment_service = EquipmentService()
        try:
            equipment_service.assign_equipment(
                equipment_id, form.assignee.data.strip(),
                expected_updated_at=expected_updated_at, username=current_user.username,
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template("error.html", error=str(e), status_code=409), 409
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        flash("Equipment assigned successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))

    @app.route("/equipment/<int:equipment_id>/unassign", methods=["POST"])
    @login_required
    @admin_required
    def equipment_unassign(equipment_id):
        form = UnassignForm()
        if not form.validate_on_submit():
            flash("Invalid request.", "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        expected_updated_at = _parse_expected_updated_at(form.expected_updated_at.data)
        equipment_service = EquipmentService()
        try:
            equipment_service.unassign_equipment(
                equipment_id, expected_updated_at=expected_updated_at, username=current_user.username,
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template("error.html", error=str(e), status_code=409), 409
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        flash("Equipment unassigned successfully.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))

    @app.route("/equipment/<int:equipment_id>/status", methods=["POST"])
    @login_required
    @admin_required
    def equipment_status(equipment_id):
        form = ChangeStatusForm()
        if not form.validate_on_submit():
            flash("Status is required.", "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        expected_updated_at = _parse_expected_updated_at(form.expected_updated_at.data)
        equipment_service = EquipmentService()
        try:
            equipment_service.change_status(
                equipment_id, form.status.data.strip(),
                expected_updated_at=expected_updated_at, username=current_user.username,
            )
        except ConflictError as e:
            flash(str(e), "error")
            return render_template("error.html", error=str(e), status_code=409), 409
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))

        flash(f"Equipment status changed to '{form.status.data}'.", "success")
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
        settings_form = SettingsForm(obj=config)
        add_category_form = AddCategoryForm()
        category_service = CategoryService()
        categories = category_service.list_categories()
        delete_category_form = DeleteCategoryForm()
        user_service = UserService()
        users = user_service.list_users()
        return render_template(
            "settings.html",
            config=config,
            settings_form=settings_form,
            add_category_form=add_category_form,
            delete_category_form=delete_category_form,
            categories=categories,
            users=users,
        )

    @app.route("/settings", methods=["POST"])
    @login_required
    @admin_required
    def settings_update():
        form = SettingsForm()
        if not form.validate_on_submit():
            flash("Invalid input.", "error")
            return redirect(url_for("settings"))

        logo_file = form.logo.data
        config_service = ConfigService()
        try:
            config_service.update_config(
                company_name=form.company_name.data.strip() or None,
                app_title=form.app_title.data.strip() or None,
                site_url=form.site_url.data.strip() if form.site_url.data else "",
                logo_file=logo_file if logo_file and hasattr(logo_file, "filename") and logo_file.filename else None,
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
        form = AddCategoryForm()
        if not form.validate_on_submit():
            flash("Category name is required.", "error")
            return redirect(url_for("settings"))

        category_service = CategoryService()
        try:
            category_service.add_category(form.name.data.strip())
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings"))

        flash(f"Category '{form.name.data.strip()}' added.", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/categories/<int:category_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def settings_delete_category(category_id):
        form = DeleteCategoryForm()
        if not form.validate_on_submit():
            flash("Invalid request.", "error")
            return redirect(url_for("settings"))

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
        create_user_form = CreateUserForm()
        delete_user_form = DeleteUserForm()
        change_role_form = ChangeRoleForm()
        return render_template(
            "users.html",
            users=users,
            create_user_form=create_user_form,
            delete_user_form=delete_user_form,
            change_role_form=change_role_form,
        )

    @app.route("/settings/users", methods=["POST"])
    @login_required
    @admin_required
    def settings_create_user():
        form = CreateUserForm()
        if not form.validate_on_submit():
            errors = []
            for field, field_errors in form.errors.items():
                for err in field_errors:
                    errors.append(err)
            flash(" ".join(errors), "error")
            return redirect(url_for("settings_users"))

        user_service = UserService()
        try:
            user_service.create_user(form.username.data.strip(), form.password.data, role=form.role.data)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("settings_users"))

        flash(f"User '{form.username.data.strip()}' created.", "success")
        return redirect(url_for("settings_users"))

    @app.route("/settings/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def settings_delete_user(user_id):
        form = DeleteUserForm()
        if not form.validate_on_submit():
            flash("Invalid request.", "error")
            return redirect(url_for("settings_users"))

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
        form = ChangeRoleForm()
        if not form.validate_on_submit():
            flash("Role is required.", "error")
            return redirect(url_for("settings_users"))

        user_service = UserService()
        try:
            user_service.change_role(user_id, form.role.data)
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

def _form_to_equipment_data(form) -> dict:
    """Extract equipment data dict from a validated EquipmentForm."""
    data = {
        "asset_tag": form.asset_tag.data.strip(),
        "name": form.name.data.strip(),
        "category": form.category.data.strip() if form.category.data and form.category.data.strip() else None,
        "manufacturer": form.manufacturer.data.strip() if form.manufacturer.data and form.manufacturer.data.strip() else None,
        "model": form.model.data.strip() if form.model.data and form.model.data.strip() else None,
        "serial_number": form.serial_number.data.strip() if form.serial_number.data and form.serial_number.data.strip() else None,
        "purchase_date": form.purchase_date.data,
        "purchase_cost": form.purchase_cost.data,
        "warranty_expiration_date": form.warranty_expiration_date.data,
    }

    if form.location.data and form.location.data.strip():
        data["location"] = form.location.data.strip()
    else:
        data["location"] = None

    if form.notes.data and form.notes.data.strip():
        data["notes"] = form.notes.data.strip()
    else:
        data["notes"] = None

    return data


def _parse_expected_updated_at(value) -> datetime | None:
    """Parse the expected_updated_at hidden field value."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
