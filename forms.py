from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    BooleanField,
    DateField,
    FloatField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class SetupForm(FlaskForm):
    company_name = StringField("Company Name", validators=[DataRequired()])
    app_title = StringField("Application Title", validators=[DataRequired()])
    site_url = StringField("Site URL", validators=[Optional()])
    logo = FileField("Company Logo", validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "svg"])])
    admin_username = StringField("Username", validators=[DataRequired()])
    admin_password = PasswordField("Password", validators=[DataRequired()])
    admin_password_confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("admin_password", message="Passwords do not match.")],
    )


ALLOWED_IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp"]


class EquipmentForm(FlaskForm):
    expected_updated_at = HiddenField()
    asset_tag = StringField("Asset Tag", validators=[DataRequired(), Length(max=100)])
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    category = SelectField("Category", validators=[DataRequired()], choices=[])
    manufacturer = StringField("Manufacturer", validators=[DataRequired(), Length(max=100)])
    model = StringField("Model", validators=[DataRequired(), Length(max=100)])
    serial_number = StringField("Serial Number", validators=[DataRequired(), Length(max=100)])
    purchase_date = DateField("Purchase Date", validators=[Optional()], format="%Y-%m-%d")
    purchase_cost = FloatField("Purchase Cost", validators=[DataRequired(), NumberRange(min=0)])
    warranty_expiration_date = DateField("Warranty Expiration Date", validators=[Optional()], format="%Y-%m-%d")
    location = StringField("Location", validators=[Optional(), Length(max=300)])
    notes = TextAreaField("Notes", validators=[Optional()])
    image = FileField("Equipment Image", validators=[Optional(), FileAllowed(ALLOWED_IMAGE_EXTENSIONS, "Images only (png, jpg, gif, webp).")])
    remove_image = BooleanField("Remove current image")


class AssignForm(FlaskForm):
    expected_updated_at = HiddenField()
    assignee = StringField("Assignee", validators=[DataRequired()])


class UnassignForm(FlaskForm):
    expected_updated_at = HiddenField()


class ChangeStatusForm(FlaskForm):
    expected_updated_at = HiddenField()
    status = SelectField(
        "Status",
        validators=[DataRequired()],
        choices=[
            ("Available", "Available"),
            ("Assigned", "Assigned"),
            ("Under Repair", "Under Repair"),
            ("Retired", "Retired"),
        ],
    )


class DeleteEquipmentForm(FlaskForm):
    """Empty form used only for CSRF protection on delete."""
    pass


class SettingsForm(FlaskForm):
    company_name = StringField("Company Name", validators=[Optional()])
    app_title = StringField("Application Title", validators=[Optional()])
    site_url = StringField("Site URL", validators=[Optional()])
    logo = FileField("Company Logo", validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "svg"])])


class AddCategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired()])


class DeleteCategoryForm(FlaskForm):
    """Empty form for CSRF on category delete."""
    pass


class CreateUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords do not match.")],
    )
    role = SelectField(
        "Role",
        choices=[("viewer", "Viewer"), ("admin", "Admin")],
        default="viewer",
    )


class DeleteUserForm(FlaskForm):
    """Empty form for CSRF on user delete."""
    pass


class ChangeRoleForm(FlaskForm):
    role = SelectField(
        "Role",
        validators=[DataRequired()],
        choices=[("viewer", "Viewer"), ("admin", "Admin")],
    )
