"""
security/rate_limiter.py
------------------------
Rate-limit configurations and per-endpoint limit decorators.

Covers:
    R10     — Brute-force login attack prevention
    R05     — DoS / request flooding prevention
    Threat  — Rate Limiting section of threat model
"""

from app import limiter


# ------------------------------------------------------------------ #
# Reusable limit strings (applied via @limiter.limit)
# ------------------------------------------------------------------ #

# Authentication endpoints — tight limits to block brute-force (R10, AUTH-04)
LOGIN_LIMIT           = "20 per minute; 100 per hour"
REGISTER_LIMIT        = "10 per hour"
CHANGE_PASSWORD_LIMIT = "5 per hour"

# Document upload — prevents storage flooding (R05)
UPLOAD_LIMIT = "10 per hour"

# General API endpoints
DEFAULT_READ_LIMIT  = "200 per hour"
DEFAULT_WRITE_LIMIT = "60 per hour"

# Admin actions — sensitive operations should be rare
ADMIN_ACTION_LIMIT = "100 per hour"


# ------------------------------------------------------------------ #
# Pre-built decorators for common patterns
# ------------------------------------------------------------------ #

def apply_login_limit(f):
    """Rate-limit for login endpoint (brute-force defence, R10)."""
    return limiter.limit(LOGIN_LIMIT)(f)


def apply_register_limit(f):
    """Rate-limit for registration endpoint."""
    return limiter.limit(REGISTER_LIMIT)(f)


def apply_upload_limit(f):
    """Rate-limit for file upload endpoints (R05)."""
    return limiter.limit(UPLOAD_LIMIT)(f)


def apply_admin_limit(f):
    """Rate-limit for admin action endpoints."""
    return limiter.limit(ADMIN_ACTION_LIMIT)(f)


# ------------------------------------------------------------------ #
# Default limit override for specific blueprints
# Applied in app.py via limiter.limit(…, blueprint=…) or
# by decorating individual views.
# ------------------------------------------------------------------ #

BLUEPRINT_LIMITS = {
    "auth":       "200 per day; 50 per hour",
    "student":    "500 per day; 100 per hour",
    "alumni":     "500 per day; 100 per hour",
    "admin":      "1000 per day; 200 per hour",
    "mentorship": "200 per day; 50 per hour",
}
