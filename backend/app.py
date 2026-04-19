"""
AlumNet - Application Factory
Initialises all extensions and registers blueprints.
Uses the factory pattern so the app can be created with different
configs (dev / test / prod) without global state.
"""

import os
import logging
from flask import Flask, jsonify, send_from_directory

from flask_cors import CORS
from flask_talisman import Talisman
from config import get_config
from extensions import db, login_manager, csrf, limiter, mail

# ------------------------------------------------------------------ #
# Resolve paths
# BACKEND_DIR  = .../alumnet/backend/
# FRONTEND_DIR = .../alumnet/frontend/
# ------------------------------------------------------------------ #
BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND_DIR, "..", "frontend")




def create_app(config_class=None):
    """
    Application factory.

    Usage:
        app = create_app()               # reads FLASK_ENV
        app = create_app(TestingConfig)  # explicit config
    """
    app = Flask(
        __name__,
        # Point Flask at the frontend folder for templates and static files
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
        static_url_path="/static",
    )

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
    # Talisman — only apply full hardening in production.
    # In debug/dev mode it forces HTTPS and sets Secure cookie flag,
    # which breaks all fetch() calls on plain HTTP localhost.
    if not app.debug:
        Talisman(
            app,
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy=app.config.get("CONTENT_SECURITY_POLICY"),
            session_cookie_secure=True,
            session_cookie_http_only=True,
        )
    else:
        # Dev: apply only safe headers (no HTTPS forcing, no Secure cookie)
        Talisman(
            app,
            force_https=False,
            strict_transport_security=False,
            content_security_policy=False,   # Avoid CSP blocking fetch in dev
            session_cookie_secure=False,
            session_cookie_http_only=True,
        )

    # ------------------------------------------------------------------ #
    # Additional security response headers (X-Content-Type-Options, etc.)
    # ------------------------------------------------------------------ #
    from security.headers import register_security_headers
    register_security_headers(app)

    # ------------------------------------------------------------------ #
    # CORS — restrict to trusted origins only
    # ------------------------------------------------------------------ #
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000")
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
    login_manager.session_protection = "strong"

    # ------------------------------------------------------------------ #
    # CSRF protection (APP-03)
    # ------------------------------------------------------------------ #
    csrf.init_app(app)

    # ------------------------------------------------------------------ #
    # Rate limiter (prevents brute-force / DoS — R10, threat model)
    # ------------------------------------------------------------------ #
    limiter.init_app(app)
    mail.init_app(app)

    # ------------------------------------------------------------------ #
    # Logging (APP-06 — security audit log)
    # ------------------------------------------------------------------ #
    _configure_logging(app)

    # ------------------------------------------------------------------ #
    # Import all models so SQLAlchemy metadata is populated before
    # db.create_all() or Alembic migrations run
    # ------------------------------------------------------------------ #
    from models.user         import User            # noqa: F401
    from models.student      import Student         # noqa: F401
    from models.alumni       import Alumni          # noqa: F401
    from models.admin        import Admin           # noqa: F401
    from models.mentorship   import MentorshipRequest      # noqa: F401
    from models.verification import VerificationDocument   # noqa: F401
    from models.audit_log    import AuditLog        # noqa: F401

    # ------------------------------------------------------------------ #
    # Register blueprints
    # ------------------------------------------------------------------ #
    from auth.routes       import auth_bp
    from routes.student    import student_bp
    from routes.alumni     import alumni_bp
    from routes.admin      import admin_bp
    from routes.mentorship import mentorship_bp

    app.register_blueprint(auth_bp,        url_prefix="/auth")
    csrf.exempt(auth_bp)   # JSON API — protected by SameSite=Strict; CSRF not needed
    app.register_blueprint(student_bp,     url_prefix="/student")
    app.register_blueprint(alumni_bp,      url_prefix="/alumni")
    app.register_blueprint(admin_bp,       url_prefix="/admin")
    app.register_blueprint(mentorship_bp,  url_prefix="/mentorship")

    # ------------------------------------------------------------------ #
    # Frontend routes — serve HTML pages directly from Flask
    # ------------------------------------------------------------------ #

    @app.route("/")
    def index():
        """Landing page."""
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/login")
    def login_page():
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "templates"), "login.html"
        )

    @app.route("/register")
    def register_page():
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "templates"), "register.html"
        )

    @app.route("/verify-email")
    def verify_email_page():
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "templates"), "verify_email.html"
        )

    @app.route("/student/dashboard")
    def student_dashboard():
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "templates"), "student_dashboard.html"
        )

    @app.route("/alumni/dashboard")
    def alumni_dashboard():
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "templates"), "alumni_dashboard.html"
        )

    @app.route("/admin/dashboard")
    def admin_dashboard():
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "templates"), "admin_panel.html"
        )

    # Serve JS files explicitly (needed because static_folder points to /static,
    # not the templates folder)
    @app.route("/static/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "static", "js"), filename
        )

    @app.route("/static/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(
            os.path.join(FRONTEND_DIR, "static", "css"), filename
        )

    # ------------------------------------------------------------------ #
    # User loader for Flask-Login
    # ------------------------------------------------------------------ #
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
        app.logger.error("Internal server error: %s", str(e))
        return jsonify({"error": "An internal error occurred."}), 500

    # ------------------------------------------------------------------ #
    # Health-check endpoint (no auth required)
    # ------------------------------------------------------------------ #
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "app": app.config["APP_NAME"]}), 200

    # ------------------------------------------------------------------ #
    # CSRF token endpoint — lets SPA/AJAX clients fetch a fresh token
    # ------------------------------------------------------------------ #
    @app.route("/csrf-token", methods=["GET"])
    def csrf_token():
        from security.csrf import get_csrf_token
        return jsonify({"csrf_token": get_csrf_token()}), 200

    # ------------------------------------------------------------------ #
    # Create tables in dev / test (use Alembic migrations in production)
    # ------------------------------------------------------------------ #
    with app.app_context():
        if app.config.get("TESTING"):
            # Tests use in-memory DB — full reset is fine and expected.
            db.drop_all()
            db.create_all()
        else:
            # Dev & production: only create tables that don't exist yet.
            # This preserves all registered users across server restarts.
            # If you change the schema, delete alumnet_dev.db once manually,
            # or use Alembic migrations.
            db.create_all()
        _seed_admin(app)

    return app



# ------------------------------------------------------------------ #
# Admin seeding — runs once on startup, idempotent
# ------------------------------------------------------------------ #
def _seed_admin(app):
    """Create the default admin account if it does not exist."""
    from models.user import User
    from auth.utils  import hash_password

    with app.app_context():
        if User.query.filter_by(username="admin").first():
            return  # already exists

        admin = User(
            email          = "admin@alumnet.edu.pk",
            username       = "admin",
            full_name      = "Platform Admin",
            password_hash  = hash_password("Admin@123"),
            role           = "admin",
            account_status = "approved",
            email_verified = True,
        )
        db.session.add(admin)
        db.session.commit()
        app.logger.info("✅ Default admin account created (username: admin)")


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

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    app.logger.info(
        "AlumNet logging initialised — level: %s", app.config.get("LOG_LEVEL")
    )


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
