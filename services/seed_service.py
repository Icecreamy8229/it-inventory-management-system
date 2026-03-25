import os
import yaml

from services.config_service import ConfigService


def seed_from_config(config_path: str = "config.yaml") -> bool:
    """Read config.yaml and run initial setup if not already complete.

    Returns True if seeding was performed, False if skipped.
    """
    config_service = ConfigService()

    if config_service.is_setup_complete():
        return False

    if not os.path.exists(config_path):
        return False

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    if not cfg:
        return False

    config_service.save_setup(
        company_name=cfg.get("company_name", "My Company"),
        app_title=cfg.get("app_title", "Equipment Inventory"),
        site_url=cfg.get("site_url", ""),
        categories=cfg.get("categories"),
        admin_username=cfg.get("admin_username"),
        admin_password=cfg.get("admin_password"),
    )

    return True
