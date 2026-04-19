"""
AlumNet - Application Factory
"""

import os
import logging
from flask import Flask, jsonify, send_from_directory

from config import get_config

BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BACKEND_DIR, "..", "frontend")

# Single source of truth — all extensions come from extensions.py
from extensions import db, login_manager, csrf, limiter, mail


def create_app(config_class=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
        static_url_path="/static",
    )

    cfg = config_class or get_config()
    app.config.from_object(cfg)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from flask_talisman import Talisman
    if not app.debug:
        Talisman(app, force_https=True, strict_transport_security=True,
                 strict_transport_security_max_age=31536000,
                 content_security_policy=app.config.get("CONTENT_SECURITY_POLICY"),
                 session_cookie_secure=True, session_cookie_http_only=True)
    else:
        Talisman(app, force_https=False, strict_transport_security=False,
                 content_security_policy=False,
                 session_cookie_secure=False, session_cookie_http_only=True)

    from security.headers import register_security_headers
    register_security_headers(app)

    from flask_cors import CORS
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000")
    CORS(app, origins=allowed_origins.split(","), supports_credentials=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    _configure_logging(app)

    from models.user            import User            # noqa: F401
    from models.student         import Student         # noqa: F401
    from models.alumni          import Alumni          # noqa: F401
    from models.admin           import Admin           # noqa: F401
    from models.work_experience import WorkExperience  # noqa: F401
    from models.mentorship      import MentorshipRequest      # noqa: F401
    from models.verification    import VerificationDocument   # noqa: F401
    from models.audit_log       import AuditLog        # noqa: F401

    from auth.routes       import auth_bp
    from routes.student    import student_bp
    from routes.alumni     import alumni_bp
    from routes.admin      import admin_bp
    from routes.mentorship import mentorship_bp

    app.register_blueprint(auth_bp,        url_prefix="/auth")
    csrf.exempt(auth_bp)
    app.register_blueprint(student_bp,     url_prefix="/student")
    app.register_blueprint(alumni_bp,      url_prefix="/alumni")
    app.register_blueprint(admin_bp,       url_prefix="/admin")
    app.register_blueprint(mentorship_bp,  url_prefix="/mentorship")

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/login")
    def login_page():
        return send_from_directory(os.path.join(FRONTEND_DIR, "templates"), "login.html")

    @app.route("/register")
    def register_page():
        return send_from_directory(os.path.join(FRONTEND_DIR, "templates"), "register.html")

    @app.route("/student/dashboard")
    def student_dashboard():
        return send_from_directory(os.path.join(FRONTEND_DIR, "templates"), "student_dashboard.html")

    @app.route("/alumni/dashboard")
    def alumni_dashboard():
        return send_from_directory(os.path.join(FRONTEND_DIR, "templates"), "alumni_dashboard.html")

    @app.route("/admin/dashboard")
    def admin_dashboard():
        return send_from_directory(os.path.join(FRONTEND_DIR, "templates"), "admin_panel.html")

    @app.route("/pending")
    def pending_approval():
        return send_from_directory(os.path.join(FRONTEND_DIR, "templates"), "pending.html")

    @app.route("/static/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "static", "js"), filename)

    @app.route("/static/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "static", "css"), filename)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

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

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "app": app.config["APP_NAME"]}), 200

    @app.route("/csrf-token", methods=["GET"])
    def csrf_token():
        from security.csrf import get_csrf_token
        return jsonify({"csrf_token": get_csrf_token()}), 200

    with app.app_context():
        if app.config.get("TESTING") or app.config.get("DEBUG"):
            db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    """Create the default admin account on first startup."""
    from models.user import User
    from models.admin import Admin
    from auth.utils import hash_password

    if User.query.filter_by(username="admin").first():
        return

    admin_user = User(
        email="admin@alumnet.giki.edu.pk",
        username="admin",
        full_name="System Administrator",
        password_hash=hash_password("Admin@123"),
        role="admin",
        account_status="approved",
        email_verified=True,
        is_active=True,
    )
    db.session.add(admin_user)
    db.session.flush()

    admin_profile = Admin(
        user_id=admin_user.id,
        department="IT Administration",
        access_level="super_admin",
    )
    db.session.add(admin_profile)
    db.session.commit()
    app.logger.info("DEFAULT ADMIN CREATED — username=admin  password=Admin@123")


def _configure_logging(app):
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    log_file  = app.config.get("LOG_FILE", "logs/alumnet.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    fh = logging.FileHandler(log_file)
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    app.logger.setLevel(log_level)
    app.logger.addHandler(fh)
    app.logger.addHandler(ch)
    app.logger.info("AlumNet logging initialised — level: %s", app.config.get("LOG_LEVEL"))


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=flask_app.config.get("DEBUG", False),
    )
