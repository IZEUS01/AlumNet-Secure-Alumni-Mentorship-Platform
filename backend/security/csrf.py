"""
security/csrf.py
----------------
CSRF protection helpers and utilities.

Flask-WTF's CSRFProtect (initialised in app.py) automatically protects
all POST/PUT/DELETE form submissions. This module adds:
  - A helper to read the token for SPA/AJAX clients
  - An exempt decorator for API endpoints that use token-based auth instead

Covers:
    APP-03  — CSRF tokens implemented for all state-changing requests
"""

from functools import wraps
from flask import jsonify, request, current_app
from flask_wtf.csrf import generate_csrf, validate_csrf, ValidationError


# ------------------------------------------------------------------ #
# Token generation helper (for AJAX / SPA clients)
# ------------------------------------------------------------------ #

def get_csrf_token() -> str:
    """
    Return a fresh CSRF token string.
    Expose this via a GET endpoint so JavaScript clients can embed it
    in subsequent POST/PUT/DELETE requests as X-CSRFToken header.
    """
    return generate_csrf()


# ------------------------------------------------------------------ #
# Manual token validation (for non-form API requests)
# ------------------------------------------------------------------ #

def validate_csrf_token() -> tuple[bool, str]:
    """
    Validate the CSRF token from the request header or JSON body.
    Returns (is_valid: bool, error_message: str).

    Clients should send the token in the X-CSRFToken request header.
    """
    token = (
        request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
        or (request.get_json(silent=True) or {}).get("csrf_token")
    )
    if not token:
        return False, "CSRF token missing."
    try:
        validate_csrf(token)
        return True, ""
    except ValidationError as e:
        current_app.logger.warning(
            "CSRF_VALIDATION_FAILED ip=%s path=%s reason=%s",
            request.remote_addr, request.path, str(e),
        )
        return False, "CSRF token invalid or expired."


# ------------------------------------------------------------------ #
# Exemption decorator for pure-API endpoints using JWT auth
# ------------------------------------------------------------------ #

def csrf_exempt_api(f):
    """
    Mark a route as CSRF-exempt.
    Use ONLY for stateless API endpoints authenticated by JWT Bearer token,
    where CSRF is not applicable.
    Never use on session-authenticated form endpoints.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    decorated._csrf_exempt = True
    return decorated
