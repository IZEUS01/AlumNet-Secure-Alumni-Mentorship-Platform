"""
AlumNet - Configuration Module
Loads all settings from environment variables.
Never hardcode secrets — all sensitive values come from .env
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared across all environments."""

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME = "AlumNet"
    DEBUG = False
    TESTING = False

    # ------------------------------------------------------------------ #
    # Secret Key (AUTH-05 — secure session tokens)
    # MUST be set in .env — never leave as default in production
    # ------------------------------------------------------------------ #
    SECRET_KEY = os.environ.get("SECRET_KEY") or "CHANGE-ME-IN-DOT-ENV"

    # ------------------------------------------------------------------ #
    # Database (DATA-05 — ORM-only, no raw SQL)
    # ------------------------------------------------------------------ #
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///alumnet_dev.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,          # Drop stale connections
        "pool_recycle": 300,
    }

    # ------------------------------------------------------------------ #
    # Session Security (AUTH-05, AUTH-06, AUTH-07)
    # ------------------------------------------------------------------ #
    SESSION_COOKIE_HTTPONLY = True      # No JS access to session cookie
    SESSION_COOKIE_SECURE = True        # HTTPS only (APP-04)
    SESSION_COOKIE_SAMESITE = "Strict"  # CSRF mitigation
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # Inactivity timeout

    # ------------------------------------------------------------------ #
    # JWT (used alongside session for API endpoints)
    # ------------------------------------------------------------------ #
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "CHANGE-JWT-SECRET"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_ALGORITHM = "HS256"

    # ------------------------------------------------------------------ #
    # CSRF (APP-03)
    # ------------------------------------------------------------------ #
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600         # 1 hour

    # ------------------------------------------------------------------ #
    # File Upload Security (DATA-02, DATA-03, DATA-04)
    # ------------------------------------------------------------------ #
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024   # 5 MB hard cap
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }
    # Uploads directory must NOT be under any static/public folder (DATA-04)

    # ------------------------------------------------------------------ #
    # Rate Limiting (prevents brute-force & DoS — R10, threat model)
    # ------------------------------------------------------------------ #
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL") or "memory://"
    RATELIMIT_HEADERS_ENABLED = True    # Expose X-RateLimit-* headers

    # ------------------------------------------------------------------ #
    # Account Lockout (AUTH-04)
    # ------------------------------------------------------------------ #
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    # ------------------------------------------------------------------ #
    # Password Policy (AUTH-03)
    # ------------------------------------------------------------------ #
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True

    # ------------------------------------------------------------------ #
    # Logging (APP-06)
    # ------------------------------------------------------------------ #
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "logs/alumnet.log")

    # ------------------------------------------------------------------ #
    # HTTPS / HSTS (APP-04)
    # ------------------------------------------------------------------ #
    FORCE_HTTPS = True
    TALISMAN_FORCE_HTTPS = True
    TALISMAN_STRICT_TRANSPORT_SECURITY = True
    TALISMAN_STRICT_TRANSPORT_SECURITY_MAX_AGE = 31536000  # 1 year
    CONTENT_SECURITY_POLICY = {
        "default-src": "'self'",
        "script-src":  "'self'",
        "style-src":   "'self'",
        "img-src":     "'self' data:",
        "object-src":  "'none'",
    }


class DevelopmentConfig(Config):
    """Development overrides — relaxed for local testing only."""
    DEBUG = True
    FORCE_HTTPS = False
    TALISMAN_FORCE_HTTPS = False
    SESSION_COOKIE_SECURE = False       # Allow HTTP in dev
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or \
        "sqlite:///alumnet_dev.db"
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """Testing overrides — in-memory DB, CSRF disabled for test client."""
    TESTING = True
    DEBUG = True
    FORCE_HTTPS = False
    TALISMAN_FORCE_HTTPS = False
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False            # Disabled for test client only
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production — all hardening enabled, secrets MUST come from env."""

    def __init__(self):
        required = ["SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {missing}"
            )


# ------------------------------------------------------------------ #
# Config selector
# ------------------------------------------------------------------ #
config_map = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development").lower()
    return config_map.get(env, DevelopmentConfig)
