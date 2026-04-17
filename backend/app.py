"""
AlumNet - Application Factory
Initialises all extensions and registers blueprints.
Uses the factory pattern so the app can be created with different
configs (dev / test / prod) without global state.
"""

import os
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_talisman import Talisman

from config import get_config

# ------------------------------------------------------------------ #
# Extension instances (not bound to any app yet)
# ------------------------------------------------------------------ #
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=None):
    """
    Application factory.

    Usage:
        app = create_app()                      # reads FLASK_ENV
        app = create_app(TestingConfig)         # explicit config
    """
    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    # Load configuration
    # ------------------------------------------------------------------ #
    cfg = config_class or get_config()
    app.config.from_object(cfg)

    # Ensure upload directory exists and is not web-accessible (DATA-04)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ------------------------------------------------------------------ #
    # Security headers (APP-04)
    # Flask-Talisman adds HSTS, CSP, X-Frame-Options, etc.
    # ------------------------------------------------------------------ #
    Talisman(
        app,
        force_https=app.config.get("TALISMAN_FORCE_HTTPS", True),
        strict_transport_security=app.config.get(
            "TALISMAN_STRICT_TRANSPORT_SECURITY", True
        ),
        strict_transport_security_max_age=app.config.get(
            "TALISMAN_STRICT_TRANSPORT_SECURITY_MAX_AGE", 31536000
        ),
        content_security_policy=app.config.get("CONTENT_SECURITY_POLICY"),
        session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", True),
        session_cookie_http_only=True,
    )

    # ------------------------------------------------------------------ #
    # CORS — restrict to trusted origins only
    # ------------------------------------------------------------------ #
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5500")
    CORS(app, origins=allowed_origins.split(","), supports_credentials=True)

    # ------------------------------------------------------------------ #
    # Database (DATA-05 — SQLAlchemy ORM prevents raw SQL injection)
    # ------------------------------------------------------------------ #
    db.init_app(app)

    # ------------------------------------------------------------------ #
    # Login manager (AUTH-05, AUTH-06, AUTH-07)
    # ------------------------------------------------------------------ #
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"   # Re-validates session on each request

    # ------------------------------------------------------------------ #
    # CSRF protection (APP-03)
    # ------------------------------------------------------------------ #
    csrf.init_app(app)

    # ------------------------------------------------------------------ #
    # Rate limiter (prevents brute-force / DoS — R10, threat model)
    # ------------------------------------------------------------------ #
    limiter.init_app(app)

    # ------------------------------------------------------------------ #
    # Logging (APP-06 — security audit log)
    # ------------------------------------------------------------------ #
    _configure_logging(app)

    # ------------------------------------------------------------------ #
    # Register blueprints
    # ------------------------------------------------------------------ #
    from auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Other blueprints (registered as you build them)
    # from routes.student  import student_bp
    # from routes.alumni   import alumni_bp
    # from routes.admin    import admin_bp
    # from routes.mentorship import mentorship_bp
    # app.register_blueprint(student_bp,    url_prefix="/student")
    # app.register_blueprint(alumni_bp,     url_prefix="/alumni")
    # app.register_blueprint(admin_bp,      url_prefix="/admin")
    # app.register_blueprint(mentorship_bp, url_prefix="/mentorship")

    # ------------------------------------------------------------------ #
    # User loader for Flask-Login
    # ------------------------------------------------------------------ #
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------ #
    # Global error handlers (APP-05 — no sensitive error info to client)
    # ------------------------------------------------------------------ #
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request."}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Authentication required."}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Access denied."}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({"error": "Too many requests. Please slow down."}), 429

    @app.errorhandler(500)
    def internal_error(e):
        # Log full detail server-side; return generic message to client
        app.logger.error("Internal server error: %s", str(e))
        return jsonify({"error": "An internal error occurred."}), 500

    # ------------------------------------------------------------------ #
    # Health-check endpoint (no auth required)
    # ------------------------------------------------------------------ #
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "app": app.config["APP_NAME"]}), 200

    # ------------------------------------------------------------------ #
    # Create tables in dev / test (use migrations in production)
    # ------------------------------------------------------------------ #
    with app.app_context():
        if app.config.get("TESTING") or app.config.get("DEBUG"):
            db.create_all()

    return app


# ------------------------------------------------------------------ #
# Logging helper
# ------------------------------------------------------------------ #
def _configure_logging(app: Flask):
    """
    Set up structured logging to file + console.
    Captures authentication events and suspicious activity (APP-06).
    """
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    log_file  = app.config.get("LOG_FILE", "logs/alumnet.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    app.logger.info("AlumNet logging initialised — level: %s", app.config.get("LOG_LEVEL"))


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=flask_app.config.get("DEBUG", False),
    )
