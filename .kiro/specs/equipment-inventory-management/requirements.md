# Requirements Document

## Introduction

A web-based equipment inventory management system for IT Administrators at a medium-sized company. The system enables tracking of IT equipment throughout its lifecycle, including registration, assignment, status updates, search, and disposal. The goal is to provide a centralized, reliable source of truth for all company equipment. The system is built as a web application with a Python/Flask backend.

## Glossary

- **System**: The Equipment Inventory Management System application
- **Administrator**: An IT Administrator who manages and tracks company equipment
- **Equipment**: A physical IT asset such as a laptop, monitor, keyboard, server, or networking device
- **Equipment_Record**: A data entry in the System representing a single piece of Equipment, including its attributes and history
- **Assignment**: The association of an Equipment_Record with a specific employee or department
- **Status**: The current state of an Equipment_Record (e.g., Available, Assigned, Under Repair, Retired)
- **Category**: A classification grouping for Equipment (e.g., Laptops, Monitors, Peripherals, Servers, Networking)
- **Asset_Tag**: A unique identifier for each Equipment_Record, sourced from a pre-printed physical barcode label affixed to the Equipment
- **Barcode_Scanner**: A USB barcode scanner device that emulates keyboard input, typing the scanned barcode value into the currently focused input field
- **Location**: An optional free-text field describing where the Equipment is physically located (e.g., building, room, floor)
- **Notes**: An optional free-text field for any additional type-specific information about the Equipment (e.g., "color printer", "has USB-C")
- **SystemConfig**: A singleton configuration record storing branding settings (Company Name, Application Title, logo path) and the setup completion flag
- **Setup_Wizard**: A first-run configuration flow that collects branding, category settings, and the initial Admin account before the System is usable
- **User**: A person with an account in the System who can log in and interact with the application
- **Role**: A permission level assigned to a User — either Admin (full access) or Viewer (read-only access)
- **Admin**: A User with full access to all System features including creating, editing, deleting equipment, managing assignments, changing settings, and managing other Users
- **Viewer**: A User with read-only access who can view equipment lists, search, view details, and view the dashboard, but cannot create, edit, delete, assign, or change settings
- **Session**: A server-side authentication session managed by Flask-Login that tracks the currently logged-in User

## Requirements

### Requirement 1: Register New Equipment

**User Story:** As an Administrator, I want to register new equipment in the system, so that I can maintain a complete inventory of all company IT assets.

#### Acceptance Criteria

1. WHEN the Administrator submits a new equipment registration form, THE System SHALL create an Equipment_Record with the following attributes: Asset_Tag, name, Category, manufacturer, model, serial number, purchase date, purchase cost, warranty expiration date, and optionally Location and Notes.
2. THE System SHALL provide an Asset_Tag input field that accepts both manual keyboard entry and input from a USB Barcode_Scanner.
3. WHEN the Asset_Tag input field receives a rapid sequence of characters followed by an Enter keypress (characteristic of a Barcode_Scanner), THE System SHALL treat the input as a scanned barcode value and populate the field accordingly.
4. IF the Administrator submits a registration form with a duplicate Asset_Tag, THEN THE System SHALL reject the submission and display an error message stating the Asset_Tag already exists.
5. IF the Administrator submits a registration form with missing required fields, THEN THE System SHALL display a validation error indicating the missing fields.
6. IF the Administrator submits a registration form with a duplicate serial number, THEN THE System SHALL reject the submission and display an error message stating the serial number already exists.

### Requirement 2: View and Search Equipment

**User Story:** As an Administrator, I want to view and search the equipment inventory, so that I can quickly find specific assets and review the overall inventory.

#### Acceptance Criteria

1. THE System SHALL display a list of all Equipment_Records with their Asset_Tag, name, Category, Status, current Assignment, and Location.
2. WHEN the Administrator enters a search query (via keyboard or Barcode_Scanner), THE System SHALL filter Equipment_Records by Asset_Tag, name, serial number, Category, assigned employee, Location, or Notes.
3. WHEN the search input field receives a rapid sequence of characters followed by an Enter keypress (characteristic of a Barcode_Scanner), THE System SHALL immediately execute the search using the scanned value.
4. WHEN the Administrator selects a sorting option, THE System SHALL sort the equipment list by the selected field in ascending or descending order.
5. WHEN the Administrator selects an Equipment_Record from the list, THE System SHALL display the full details of that Equipment_Record, including Location and Notes if present.
6. WHEN a barcode scan search matches exactly one Equipment_Record by Asset_Tag, THE System SHALL navigate directly to that Equipment_Record's detail view.

### Requirement 3: Update Equipment Details

**User Story:** As an Administrator, I want to update equipment details, so that the inventory reflects the current state of each asset.

#### Acceptance Criteria

1. WHEN the Administrator submits an update to an Equipment_Record, THE System SHALL save the changes and display a confirmation message.
2. IF the Administrator submits an update with invalid data, THEN THE System SHALL display a validation error describing the invalid fields.
3. WHEN an Equipment_Record is updated, THE System SHALL record the date and nature of the change in the Equipment_Record history.
4. IF the Equipment_Record has been modified by another User since the edit form was loaded, THEN THE System SHALL reject the update and display a conflict error message instructing the Administrator to refresh and try again.

### Requirement 4: Assign and Unassign Equipment

**User Story:** As an Administrator, I want to assign equipment to employees or departments and unassign equipment when returned, so that I can track who has which assets.

#### Acceptance Criteria

1. WHEN the Administrator assigns an Equipment_Record to an employee or department, THE System SHALL update the Assignment field and set the Status to "Assigned".
2. WHEN the Administrator unassigns an Equipment_Record, THE System SHALL clear the Assignment field and set the Status to "Available".
3. IF the Administrator attempts to assign an Equipment_Record that has a Status of "Retired" or "Under Repair", THEN THE System SHALL reject the assignment and display an error message stating the equipment is not available for assignment.
4. WHEN an Assignment change occurs, THE System SHALL record the Assignment change with the date, previous Assignment, and new Assignment in the Equipment_Record history.
5. IF the Equipment_Record has been modified by another User since the assign/unassign form was loaded, THEN THE System SHALL reject the operation and display a conflict error message instructing the Administrator to refresh and try again.

### Requirement 5: Track Equipment Status

**User Story:** As an Administrator, I want to update and track the status of equipment, so that I know which assets are available, in use, under repair, or retired.

#### Acceptance Criteria

1. THE System SHALL support the following Status values: Available, Assigned, Under Repair, and Retired.
2. WHEN the Administrator changes the Status of an Equipment_Record, THE System SHALL save the new Status and record the change with a timestamp in the Equipment_Record history.
3. IF the Administrator changes the Status of an Equipment_Record to "Retired", THEN THE System SHALL clear the Assignment field if one exists.
4. WHILE an Equipment_Record has a Status of "Retired", THE System SHALL prevent any new Assignments to that Equipment_Record.
5. IF the Equipment_Record has been modified by another User since the status change form was loaded, THEN THE System SHALL reject the status change and display a conflict error message instructing the Administrator to refresh and try again.

### Requirement 6: Delete Equipment Records

**User Story:** As an Administrator, I want to delete equipment records that were created in error, so that the inventory remains accurate.

#### Acceptance Criteria

1. WHEN the Administrator requests deletion of an Equipment_Record, THE System SHALL prompt the Administrator for confirmation before deleting.
2. WHEN the Administrator confirms deletion, THE System SHALL remove the Equipment_Record from the inventory and display a confirmation message.
3. IF the Administrator cancels the deletion, THEN THE System SHALL retain the Equipment_Record without changes.

### Requirement 7: Equipment Summary Dashboard

**User Story:** As an Administrator, I want to see a summary dashboard of the equipment inventory, so that I can get a quick overview of asset distribution and status.

#### Acceptance Criteria

1. THE System SHALL display a dashboard showing the total count of Equipment_Records grouped by Status.
2. THE System SHALL display a dashboard showing the total count of Equipment_Records grouped by Category.
3. WHEN an Equipment_Record is created, updated, or deleted, THE System SHALL reflect the change on the dashboard without requiring a manual refresh by the Administrator.

### Requirement 8: Docker Deployment

**User Story:** As an Administrator, I want to launch the system as a Docker container, so that deployment is simple and consistent across environments.

#### Acceptance Criteria

1. WHEN the Administrator runs a Docker build command against the project, THE System SHALL produce a valid Docker image containing the application and all its dependencies.
2. WHEN the Administrator runs the Docker container with a single command, THE System SHALL start the application and begin serving HTTP requests.
3. WHEN the Administrator specifies a port mapping at container launch, THE System SHALL be accessible on the configured host port.
4. WHEN the Administrator mounts a Docker volume to the container's SQLite data directory, THE System SHALL persist all database data across container restarts and re-creations.

### Requirement 9: First-Run Setup Wizard

**User Story:** As an Administrator, I want to be guided through initial system configuration on first launch, so that the application is branded, customized, and secured for my company before use.

#### Acceptance Criteria

1. WHEN the System detects no configuration exists (first launch), THE System SHALL redirect the Administrator to a setup wizard page.
2. WHILE the setup wizard has not been completed, THE System SHALL redirect all other routes to the setup wizard page.
3. THE setup wizard SHALL collect the following information: Company Name, Application Title, and Company Logo (file upload).
4. THE setup wizard SHALL display a list of default equipment categories (Laptops, Monitors, Peripherals, Servers, Networking) that the Administrator can add to or remove from before completing setup.
5. WHEN the Administrator completes the setup wizard, THE System SHALL save the configuration and redirect to the dashboard.
6. WHEN a Company Logo is uploaded, THE System SHALL store the file in a persistent volume-mounted directory.
7. THE setup wizard SHALL collect an initial Admin account username and password.
8. WHEN the Administrator completes the setup wizard, THE System SHALL create a User account with the provided username and password (hashed) and assign it the Admin Role.

### Requirement 10: Settings Management

**User Story:** As an Administrator, I want to update branding and category settings after initial setup, so that I can adjust the system configuration as needs change.

#### Acceptance Criteria

1. THE System SHALL provide a Settings page where the Administrator can update Company Name, Application Title, and Company Logo.
2. THE System SHALL allow the Administrator to add new equipment categories from the Settings page.
3. THE System SHALL allow the Administrator to remove equipment categories from the Settings page.
4. IF the Administrator attempts to remove a Category that is currently assigned to one or more Equipment_Records, THEN THE System SHALL reject the removal and display an error message stating the category is in use.
5. WHEN the Administrator saves settings changes, THE System SHALL apply the changes immediately without requiring a restart.


### Requirement 11: User Authentication

**User Story:** As a User, I want to log in with my username and password, so that only authorized people can access the system.

#### Acceptance Criteria

1. WHEN a User navigates to any route other than `/login`, AND the User is not authenticated, THEN THE System SHALL redirect the User to the login page.
2. WHEN a User submits valid credentials on the login page, THE System SHALL authenticate the User, create a session, and redirect to the dashboard.
3. WHEN a User submits invalid credentials on the login page, THE System SHALL reject the login and display an error message without revealing which field was incorrect.
4. WHEN an authenticated User requests to log out, THE System SHALL terminate the session and redirect to the login page.
5. THE System SHALL store passwords as hashed values and SHALL NOT store plaintext passwords.

### Requirement 12: Role-Based Access Control

**User Story:** As an Admin, I want to control what different users can do in the system, so that Viewers can see inventory information without accidentally modifying it.

#### Acceptance Criteria

1. WHEN a User with the Admin Role is authenticated, THE System SHALL allow full access to all features including creating, editing, deleting Equipment_Records, managing Assignments, changing Status, updating Settings, and managing Users.
2. WHEN a User with the Viewer Role is authenticated, THE System SHALL allow read-only access: viewing the equipment list, searching, viewing Equipment_Record details, and viewing the dashboard.
3. WHEN a User with the Viewer Role attempts a write operation (create, edit, delete, assign, unassign, change status, or update settings), THE System SHALL reject the request and return a forbidden error.
4. WHEN a new User account is created, THE System SHALL assign the Viewer Role by default.
5. WHEN an Admin creates a new User from the Settings page, THE System SHALL require a username and password and create the account with a hashed password.
6. WHEN an Admin deletes a User account, THE System SHALL remove the User from the system.
7. WHEN an Admin changes a User's Role, THE System SHALL update the Role immediately.
8. THE System SHALL only allow Users with the Admin Role to create, delete, or change the Role of other Users.
