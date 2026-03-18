from flask import redirect, url_for, request
from models import SystemConfig


def register_middleware(app):
    @app.before_request
    def setup_required():
        # Exempt routes
        exempt_endpoints = {"setup", "setup_post", "login", "login_post", "static"}
        if request.endpoint in exempt_endpoints:
            return None

        # Check if setup is complete
        config = SystemConfig.query.first()
        if config is None or not config.setup_complete:
            return redirect(url_for("setup"))
        return None
