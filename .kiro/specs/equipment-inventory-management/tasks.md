# Implementation Plan: Equipment Inventory Management

## Overview

Build a Python/Flask web application for IT equipment inventory management with SQLite persistence, Docker deployment, barcode scanner support, authentication, role-based access control, and a first-run setup wizard. Implementation proceeds bottom-up: data models → service layer → authentication → routes → templates → Docker packaging.

## Tasks

- [x] 1. Set up project structure, dependencies, and database models
  - [x] 1.1 Create project skeleton and install dependencies
    - Create `app.py` (Flask app factory), `requirements.txt` (Flask, Flask-SQLAlchemy, Flask-Login, gunicorn, hypothesis, pytest), and directory structure (`templates/`, `static/`, `services/`, `models/`, `tests/`)
    - Configure Flask app with `DATABASE_PATH` and `UPLOAD_PATH` from environment variables, defaulting to `data/equipment.db` and `data/uploads/`
    - Initialize Flask-SQLAlchemy and Flask-Login extensions
    - _Requirements: 8.1_

  - [x] 1.2 Define all SQLAlchemy data models
    - Create `Equipment`, `EquipmentHistory`, `SystemConfig`, `Category`, and `User` models as specified in the design
    - `User` extends `UserMixin` from Flask-Login
    - `Equipment.asset_tag` and `Equipment.serial_number` have unique constraints
    - `SystemConfig` is a singleton with `setup_complete` flag
    - `Category.name` has a unique constraint
    - Define `Equipment.history_entries` relationship with cascade delete
    - _Requirements: 1.1, 3.3, 4.4, 5.1, 5.2, 9.3, 11.5, 12.4_

  - [x] 1.3 Create `ConflictError` exception class
    - Define in a shared exceptions module for optimistic concurrency control
    - _Requirements: 3.4, 4.5, 5.5_

  - [ ]* 1.4 Write property test for equipment creation round-trip
    - **Property 1: Equipment creation round-trip**
    - **Validates: Requirements 1.1**

  - [x] 1.5 Create database initialization logic
    - Add `db.create_all()` call in app startup
    - Ensure `/app/data` and `/app/data/uploads` directories are created if they don't exist
    - _Requirements: 8.4_

- [x] 2. Implement validation and category service
  - [x] 2.1 Implement `CategoryService`
    - `list_categories()`, `add_category()`, `delete_category()`, `get_default_categories()`
    - `add_category` rejects duplicate names
    - `delete_category` rejects if any Equipment records reference the category
    - _Requirements: 9.4, 10.2, 10.3, 10.4_

  - [x] 2.2 Implement `validate_equipment_data` function
    - Check all required fields: asset_tag, name, category, manufacturer, model, serial_number, purchase_date, purchase_cost, warranty_expiration_date
    - Validate asset_tag uniqueness and serial_number uniqueness (skip own record on update)
    - Validate category exists in Category table
    - Location and Notes are optional
    - Return list of error messages
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 3.2_

  - [x] 2.3 Write property test for uniqueness enforcement
    - **Property 3: Uniqueness enforcement for asset tag and serial number**
    - **Validates: Requirements 1.4, 1.6**

  - [x] 2.4 Write property test for validation rejects incomplete data
    - **Property 4: Validation rejects incomplete data**
    - **Validates: Requirements 1.5, 3.2**

  - [x] 2.5 Write property test for category add/remove round-trip
    - **Property 20: Category add/remove round-trip**
    - **Validates: Requirements 10.2, 10.3**

  - [x] 2.6 Write property test for category deletion protection
    - **Property 21: Category deletion protection**
    - **Validates: Requirements 10.4**

- [x] 3. Implement equipment service layer
  - [x] 3.1 Implement `EquipmentService.create_equipment`
    - Validate data, create Equipment record with status "Available", create "Created" history entry
    - _Requirements: 1.1, 1.4, 1.5, 1.6_

  - [x] 3.2 Implement `EquipmentService.update_equipment` with optimistic concurrency
    - Validate data, compare `expected_updated_at` with record's `updated_at`, raise `ConflictError` on mismatch
    - Record "Updated" history entry with changed fields
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.3 Implement `EquipmentService.delete_equipment`
    - Delete equipment record and cascade-delete history entries
    - _Requirements: 6.2_

  - [x] 3.4 Implement `EquipmentService.assign_equipment` and `unassign_equipment`
    - `assign_equipment`: reject if status is "Retired" or "Under Repair", set assignee and status to "Assigned", record history, check optimistic concurrency
    - `unassign_equipment`: clear assignee, set status to "Available", record history, check optimistic concurrency
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.5 Implement `EquipmentService.change_status`
    - Enforce valid status values, clear assignee when retiring, check optimistic concurrency, record history
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.6 Implement `EquipmentService.list_equipment` with search and sort
    - Filter by asset_tag, name, serial_number, category, assignee, location, or notes
    - Sort by any field in ascending or descending order
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 3.7 Implement `EquipmentService.lookup_by_asset_tag` and `get_dashboard_summary`
    - `lookup_by_asset_tag`: exact match lookup for barcode scan navigation
    - `get_dashboard_summary`: return counts grouped by status and by category
    - _Requirements: 2.6, 7.1, 7.2_

  - [ ]* 3.8 Write property tests for equipment service
    - **Property 8: Update round-trip**
    - **Validates: Requirements 3.1**

  - [ ]* 3.9 Write property test for mutations create history entries
    - **Property 9: Mutations create history entries**
    - **Validates: Requirements 3.3, 4.4, 5.2**

  - [ ]* 3.10 Write property test for assign/unassign round-trip
    - **Property 10: Assign/unassign round-trip**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 3.11 Write property test for non-available equipment rejects assignment
    - **Property 11: Non-available equipment rejects assignment**
    - **Validates: Requirements 4.3, 5.4**

  - [ ]* 3.12 Write property test for only valid statuses accepted
    - **Property 12: Only valid statuses accepted**
    - **Validates: Requirements 5.1**

  - [ ]* 3.13 Write property test for retiring clears assignee
    - **Property 13: Retiring clears assignee**
    - **Validates: Requirements 5.3**

  - [ ]* 3.14 Write property test for deletion removes record
    - **Property 14: Deletion removes record**
    - **Validates: Requirements 6.2**

  - [ ]* 3.15 Write property test for search filters correctly
    - **Property 5: Search filters correctly**
    - **Validates: Requirements 2.2**

  - [ ]* 3.16 Write property test for sorting preserves ordering invariant
    - **Property 6: Sorting preserves ordering invariant**
    - **Validates: Requirements 2.4**

  - [ ]* 3.17 Write property test for exact asset tag lookup
    - **Property 7: Exact asset tag lookup**
    - **Validates: Requirements 2.6**

  - [ ]* 3.18 Write property test for dashboard counts match actual data
    - **Property 15: Dashboard counts match actual data**
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 3.19 Write property test for optimistic concurrency conflict detection
    - **Property 30: Optimistic concurrency conflict detection**
    - **Validates: Requirements 3.4, 4.5, 5.5**

- [x] 4. Checkpoint - Ensure all service layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement user service and authentication
  - [x] 5.1 Implement `UserService`
    - `create_user`: hash password with `werkzeug.security.generate_password_hash`, default role "viewer", reject duplicate usernames
    - `authenticate`: verify credentials with `check_password_hash`, return User or None
    - `delete_user`, `change_role`, `list_users`, `get_user_by_id`
    - _Requirements: 11.2, 11.3, 11.5, 12.4, 12.5, 12.6, 12.7_

  - [x] 5.2 Implement Flask-Login integration and decorators
    - Configure `LoginManager` with `login_view="login"`
    - Implement `load_user` callback using `UserService.get_user_by_id`
    - Implement `admin_required` decorator that checks `current_user.role == "admin"` and returns 403 for Viewers
    - _Requirements: 11.1, 12.1, 12.3, 12.8_

  - [x] 5.3 Implement `setup_required` middleware
    - Before-request handler that checks `SystemConfig.setup_complete`
    - Redirect to `/setup` if not complete; exempt `/setup`, `/login`, and static file routes
    - _Requirements: 9.1, 9.2_

  - [ ]* 5.4 Write property test for user creation defaults and password hashing
    - **Property 27: User creation defaults and password hashing**
    - **Validates: Requirements 11.5, 12.4, 12.5**

  - [ ]* 5.5 Write property test for invalid credentials rejection
    - **Property 24: Invalid credentials rejection**
    - **Validates: Requirements 11.3**

  - [ ]* 5.6 Write property test for user deletion removes record
    - **Property 28: User deletion removes record**
    - **Validates: Requirements 12.6**

  - [ ]* 5.7 Write property test for role change round-trip
    - **Property 29: Role change round-trip**
    - **Validates: Requirements 12.7**

- [x] 6. Implement config service and setup wizard
  - [x] 6.1 Implement `ConfigService`
    - `is_setup_complete`, `get_config`, `save_setup` (creates SystemConfig, Category records, and initial Admin user), `update_config`
    - Logo file saved to `UPLOAD_PATH` directory
    - _Requirements: 9.1, 9.3, 9.5, 9.6, 9.7, 9.8, 10.1, 10.5_

  - [ ]* 6.2 Write property test for setup configuration round-trip
    - **Property 17: Setup configuration round-trip**
    - **Validates: Requirements 9.3, 9.5, 9.7, 9.8**

  - [ ]* 6.3 Write property test for logo upload persistence
    - **Property 18: Logo upload persistence**
    - **Validates: Requirements 9.6**

  - [ ]* 6.4 Write property test for settings update round-trip
    - **Property 19: Settings update round-trip**
    - **Validates: Requirements 10.1, 10.5**

- [x] 7. Checkpoint - Ensure all service and auth tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Flask route handlers
  - [x] 8.1 Implement setup wizard routes (`/setup` GET and POST)
    - GET: render setup form with default categories
    - POST: validate inputs, call `ConfigService.save_setup`, redirect to dashboard
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [x] 8.2 Implement login/logout routes (`/login` GET/POST, `/logout` GET)
    - Login: authenticate via `UserService`, create session with `flask_login.login_user`, redirect to dashboard
    - Failed login: re-render with generic error "Invalid username or password"
    - Logout: `flask_login.logout_user`, redirect to `/login`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 8.3 Implement dashboard route (`/` GET)
    - Call `EquipmentService.get_dashboard_summary`, render dashboard template with status and category counts
    - Accessible to both Admin and Viewer roles
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 8.4 Implement equipment CRUD routes
    - `GET /equipment`: list with search/sort query params
    - `GET /equipment/scan-lookup?asset_tag=X`: lookup by exact asset tag, redirect to detail if found
    - `GET /equipment/new`: registration form (Admin only)
    - `POST /equipment`: create equipment (Admin only), include `expected_updated_at` hidden field handling
    - `GET /equipment/<id>`: detail view with history
    - `GET /equipment/<id>/edit`: edit form with `updated_at` as hidden field (Admin only)
    - `PUT/POST /equipment/<id>`: update equipment (Admin only), handle `ConflictError` → 409
    - `POST /equipment/<id>/delete`: delete with confirmation (Admin only)
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 2.1, 2.2, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 6.1, 6.2, 6.3_

  - [x] 8.5 Implement assignment and status routes
    - `POST /equipment/<id>/assign`: assign equipment (Admin only), handle `ConflictError`
    - `POST /equipment/<id>/unassign`: unassign equipment (Admin only), handle `ConflictError`
    - `POST /equipment/<id>/status`: change status (Admin only), handle `ConflictError`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 8.6 Implement settings and user management routes
    - `GET /settings`: render settings page with current config and categories (Admin only)
    - `POST /settings`: update branding (Admin only)
    - `POST /settings/categories`: add category (Admin only)
    - `POST /settings/categories/<id>/delete`: delete category (Admin only)
    - `GET /settings/users`: user list (Admin only)
    - `POST /settings/users`: create user (Admin only)
    - `POST /settings/users/<id>/delete`: delete user (Admin only)
    - `POST /settings/users/<id>/role`: change role (Admin only)
    - `GET /uploads/<filename>`: serve uploaded files
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 12.1, 12.5, 12.6, 12.7, 12.8_

  - [ ]* 8.7 Write property test for first-run redirect
    - **Property 16: First-run redirect**
    - **Validates: Requirements 9.1, 9.2**

  - [ ]* 8.8 Write property test for unauthenticated redirect
    - **Property 22: Unauthenticated redirect**
    - **Validates: Requirements 11.1**

  - [ ]* 8.9 Write property test for login/logout round-trip
    - **Property 23: Login/logout round-trip**
    - **Validates: Requirements 11.2, 11.4**

  - [ ]* 8.10 Write property test for write access requires Admin role
    - **Property 25: Write access requires Admin role**
    - **Validates: Requirements 12.1, 12.3, 12.8**

  - [ ]* 8.11 Write property test for read access for all authenticated users
    - **Property 26: Read access for all authenticated users**
    - **Validates: Requirements 12.2**

- [x] 9. Checkpoint - Ensure all route tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Jinja2 templates and frontend
  - [x] 10.1 Create base template and layout
    - Base template with navigation (brand logo, app title from SystemConfig), login/logout link, role-aware menu items
    - Include CSS for styling and responsive layout
    - _Requirements: 9.3, 10.1_

  - [x] 10.2 Create setup wizard template
    - Form for company name, app title, logo upload, category management (add/remove from defaults), admin username and password
    - _Requirements: 9.3, 9.4, 9.7_

  - [x] 10.3 Create login template
    - Username and password form, generic error display area
    - _Requirements: 11.2, 11.3_

  - [x] 10.4 Create dashboard template
    - Display counts by status and by category
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 10.5 Create equipment list template
    - Table with Asset Tag, Name, Category, Status, Assignee, Location columns
    - Search input field, sort controls
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 10.6 Create equipment detail, registration, and edit templates
    - Detail view: all fields including Location, Notes, and history entries
    - Registration form: all required fields plus optional Location and Notes, asset tag input supporting barcode scanner
    - Edit form: pre-populated fields, hidden `updated_at` field for concurrency control
    - Assign/unassign and status change forms with hidden `updated_at` fields
    - Delete confirmation dialog
    - Hide/disable write actions for Viewer role
    - _Requirements: 1.1, 1.2, 2.5, 3.1, 3.4, 4.1, 4.2, 4.5, 5.1, 5.5, 6.1, 6.3, 12.2, 12.3_

  - [x] 10.7 Create settings and user management templates
    - Settings form: company name, app title, logo upload
    - Category list with add/remove controls
    - User list with create, delete, and role change controls
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 12.5, 12.6, 12.7, 12.8_

  - [x] 10.8 Implement barcode scanner detection JavaScript module
    - Track keystroke timing on asset tag and search input fields
    - Classify rapid input (all keystrokes within 50ms) followed by Enter as barcode scan
    - On scan in search field: submit search immediately; if single match by asset tag, redirect to detail view via `/equipment/scan-lookup`
    - On scan in registration field: populate the field value
    - _Requirements: 1.2, 1.3, 2.3, 2.6_

  - [ ]* 10.9 Write property test for barcode scan detection (fast-check, JavaScript)
    - **Property 2: Barcode scan detection**
    - **Validates: Requirements 1.3**

- [x] 11. Implement Docker deployment
  - [x] 11.1 Create Dockerfile
    - Use `python:3.12-slim`, install dependencies, create `/app/data` and `/app/data/uploads` directories, expose port 5000, run with gunicorn
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 11.2 Create docker-compose.yml and .dockerignore
    - Single service with configurable port via `PORT` env var, `equipment-data` named volume mounted to `/app/data`
    - `.dockerignore` excludes `__pycache__`, `.git`, `.kiro`, `*.db`, `.env`, `venv`, `node_modules`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use Hypothesis (Python) for backend and fast-check (JavaScript) for barcode detection
- Unit tests and property tests are complementary
- All 12 requirements and 30 correctness properties are covered
