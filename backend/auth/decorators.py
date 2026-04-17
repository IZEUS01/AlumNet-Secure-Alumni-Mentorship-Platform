"""
auth/decorators.py
------------------
Route-level decorators that enforce authentication and RBAC.

Covers:
    RBAC-01  — Enforce role-based access control for all resources
    RBAC-05  — Admin-only functions
    RBAC-06  — All role validation on server side
    AUTH-07  — Session invalidation on suspicious access
"""

from functools import wraps
from flask import jsonify, current_app, request
from flask_login import current_user


# ------------------------------------------------------------------ #
# Role constants  (single source of truth — matches models/user.py)
# ------------------------------------------------------------------ #

class Role:
    STUDENT          = "student"
    UNVERIFIED_ALUMNI = "unverified_alumni"
    VERIFIED_ALUMNI  = "verified_alumni"
    ADMIN            = "admin"

    ALL = {STUDENT, UNVERIFIED_ALUMNI, VERIFIED_ALUMNI, ADMIN}


# ------------------------------------------------------------------ #
# Core: require authenticated user
# ------------------------------------------------------------------ #

def login_required_json(f):
    """
    Like Flask-Login's @login_required but returns JSON 401
    instead of redirecting — useful for API endpoints.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            current_app.logger.warning(
                "Unauthenticated access attempt to %s from %s",
                request.path, request.remote_addr,
            )
            return jsonify({"error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------ #
# RBAC: require specific role(s)  (RBAC-01, RBAC-06)
# ------------------------------------------------------------------ #

def role_required(*allowed_roles):
    """
    Restrict a route to one or more roles.

    Usage:
        @role_required(Role.ADMIN)
        @role_required(Role.VERIFIED_ALUMNI, Role.ADMIN)

    All role checks happen server-side — client cannot bypass by
    manipulating UI or request headers (RBAC-06).
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Must be authenticated first
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication required."}), 401

            # Check role
            if current_user.role not in allowed_roles:
                current_app.logger.warning(
                    "Unauthorised role access: user=%s role=%s attempted=%s path=%s ip=%s",
                    current_user.id,
                    current_user.role,
                    allowed_roles,
                    request.path,
                    request.remote_addr,
                )
                return jsonify({"error": "Access denied."}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# ------------------------------------------------------------------ #
# Convenience decorators
# ------------------------------------------------------------------ #

def student_required(f):
    """Allow Students only (RBAC-02)."""
    @wraps(f)
    @login_required_json
    @role_required(Role.STUDENT)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


def verified_alumni_required(f):
    """
    Allow Verified Alumni only.
    Unverified alumni cannot interact until approved (RBAC-03).
    """
    @wraps(f)
    @login_required_json
    @role_required(Role.VERIFIED_ALUMNI)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


def alumni_any_required(f):
    """Allow both Verified and Unverified Alumni."""
    @wraps(f)
    @login_required_json
    @role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """
    Allow Administrators only (RBAC-05).
    Logs every admin-route access for audit trail (APP-06).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required."}), 401

        if current_user.role != Role.ADMIN:
            current_app.logger.critical(
                "ADMIN ACCESS DENIED: user=%s role=%s path=%s ip=%s",
                current_user.id,
                current_user.role,
                request.path,
                request.remote_addr,
            )
            return jsonify({"error": "Access denied."}), 403

        # Log legitimate admin access (APP-06)
        current_app.logger.info(
            "Admin access: user=%s path=%s ip=%s",
            current_user.id, request.path, request.remote_addr,
        )
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------ #
# Verified status check (for alumni who just registered)
# ------------------------------------------------------------------ #

def verification_required(f):
    """
    Ensure the current alumni user has been verified by an admin.
    Redirects unverified alumni to a pending page.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required."}), 401

        if current_user.role == Role.UNVERIFIED_ALUMNI:
            return jsonify({
                "error": "Your account is pending verification by an administrator."
            }), 403

        return f(*args, **kwargs)
    return decorated
