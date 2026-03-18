# Equipment Inventory

A simple, self-hosted equipment tracking app for small and medium businesses. Track assets, assignments, warranties, and lifecycle — all from a clean web interface.

Built with Flask, SQLite, and Docker. No external database required.

## Features

- **Asset tracking** — Register equipment with asset tags, serial numbers, categories, and costs
- **Assignment management** — Assign and unassign equipment to people or departments
- **Status lifecycle** — Track equipment through Available, Assigned, Under Repair, and Retired states
- **Dashboard metrics** — Total asset value, warranty alerts, aging equipment, assignment density
- **Clickable filters** — Click any dashboard metric to see the matching equipment
- **Warranty alerts** — Surface equipment with warranties expiring in the next 90 days
- **Change history** — Full audit trail of every change, including who made it
- **Barcode lookup** — Scan or search by asset tag
- **Role-based access** — Admin and Viewer roles
- **Responsive UI** — Works on desktop and mobile with collapsible navigation
- **Custom branding** — Set your company name, app title, and logo

## Quick Start (Docker)

```bash
git clone https://github.com/Icecreamy8229/it-inventory-management-system
cd equipment-inventory
```

### Option A: Auto-seed from config file

```bash
cp config.yaml.template config.yaml
# Edit config.yaml with your company name, admin credentials, etc.
docker compose up -d
```

### Option B: Setup via browser

```bash
docker compose up -d
```

Open `http://localhost:5000` and complete the setup wizard.

## Quick Start (Local)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask run
```

Open `http://localhost:5000`.

## Configuration

### config.yaml (optional)

Copy `config.yaml.template` to `config.yaml` to pre-configure the app on first startup:

```yaml
company_name: "My Company"
app_title: "Equipment Inventory"
admin_username: "admin"
admin_password: "changeme"
categories:
  - "Laptop"
  - "Desktop"
  - "Monitor"
```

This file is only read on first startup. After setup is complete, it's ignored.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key` | Flask secret key (set this in production) |
| `DATABASE_PATH` | `data/equipment.db` | Path to SQLite database file |
| `UPLOAD_PATH` | `data/uploads` | Path for uploaded files (logos) |
| `PORT` | `5000` | Port to expose (Docker only) |

## Project Structure

```
├── app.py                  # Flask app factory
├── routes.py               # All route handlers
├── auth.py                 # Authentication helpers
├── middleware.py            # Request middleware
├── models/                 # SQLAlchemy models
├── services/               # Business logic layer
├── templates/              # Jinja2 HTML templates
├── static/                 # JS and static assets
├── tests/                  # Test suite
├── config.yaml.template    # Example config for first-run seeding
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Running Tests

```bash
pip install -r requirements.txt
pytest
```

## License

MIT
