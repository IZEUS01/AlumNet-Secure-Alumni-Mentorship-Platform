"""
auth/routes.py
--------------
Authentication endpoints: register, login, logout, change-password.

Security controls implemented here:
    AUTH-01  — Unique username/email + password authentication
    AUTH-02  — Passwords hashed before storage (via utils)
    AUTH-03  — Password complexity enforced at registration
    AUTH-04  — Account lockout after 5 failed attempts
    AUTH-05  — Secure session token issued on login
    AUTH-06  — Session expires after inactivity (configured in app)
    AUTH-07  — Logout invalidates server-side session
    APP-01   — All inputs validated server-side
    APP-05   — Generic error messages (no information leakage)
    APP-06   — Security events logged
    R01      — Brute-force protection via rate limiting + lockout
"""

import re
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, session
from flask_login import login_user, logout_user, current_user, login_required

from app import db, limiter
from models.user import User
from auth.utils import (
    hash_password,
    verify_password,
    validate_password_strength,
    normalise_email,
    is_account_locked,
    calculate_lockout_until,
    get_lockout_remaining_seconds,
)
from auth.decorators import Role

auth_bp = Blueprint("auth", __name__)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _sanitise_string(value: str, max_len: int = 255) -> str:
    """Strip whitespace and enforce max length (APP-01)."""
    return value.strip()[:max_len] if value else ""


def _is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _log_auth_event(event: str, user_id=None, email=None, ip=None, extra=None):
    """Centralised security event logging (APP-06)."""
    current_app.logger.info(
        "AUTH_EVENT event=%s user_id=%s email=%s ip=%s extra=%s",
        event, user_id, email, ip or request.remote_addr, extra,
    )


# ------------------------------------------------------------------ #
# POST /auth/register
# ------------------------------------------------------------------ #

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")          # Prevent mass account creation
def register():
    """
    Register a new user.
    Role is determined by the 'role' field (student | alumni).
    Alumni start as UNVERIFIED_ALUMNI until an admin approves.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    # ---- Extract & sanitise inputs (APP-01) ---- #
    email      = _sanitise_string(data.get("email", ""))
    username   = _sanitise_string(data.get("username", ""))
    password   = data.get("password", "")          # Don't strip — spaces are valid
    full_name  = _sanitise_string(data.get("full_name", ""))
    role_input = _sanitise_string(data.get("role", "student")).lower()

    # ---- Input validation (APP-01) ---- #
    errors = {}

    if not email or not _is_valid_email(email):
        errors["email"] = "A valid email address is required."

    if not username or len(username) < 3:
        errors["username"] = "Username must be at least 3 characters."

    if not full_name:
        errors["full_name"] = "Full name is required."

    if role_input not in ("student", "alumni"):
        errors["role"] = "Role must be 'student' or 'alumni'."

    # Password complexity (AUTH-03)
    if not password:
        errors["password"] = "Password is required."
    else:
        is_strong, pw_errors = validate_password_strength(password)
        if not is_strong:
            errors["password"] = pw_errors

    if errors:
        return jsonify({"errors": errors}), 422

    # ---- Normalise email ---- #
    email = normalise_email(email)

    # ---- Check for duplicate email / username ---- #
    if User.query.filter_by(email=email).first():
        # Generic message to avoid user enumeration (APP-05)
        return jsonify({"error": "Registration failed. Please try again."}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Registration failed. Please try again."}), 409

    # ---- Assign role ---- #
    assigned_role = (
        Role.UNVERIFIED_ALUMNI if role_input == "alumni" else Role.STUDENT
    )

    # ---- Hash password before storage (AUTH-02) ---- #
    hashed_pw = hash_password(password)

    # ---- Persist new user ---- #
    new_user = User(
        email=email,
        username=username,
        password_hash=hashed_pw,
        full_name=full_name,
        role=assigned_role,
    )
    db.session.add(new_user)
    db.session.commit()

    _log_auth_event("REGISTER_SUCCESS", user_id=new_user.id, email=email)

    return jsonify({
        "message": "Registration successful.",
        "role": assigned_role,
        "pending_verification": assigned_role == Role.UNVERIFIED_ALUMNI,
    }), 201


# ------------------------------------------------------------------ #
# POST /auth/login
# ------------------------------------------------------------------ #

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per minute;100 per hour")   # Rate-limit login (R01, AUTH-04)
def login():
    """
    Authenticate a user and issue a server-side session (AUTH-05).
    Enforces account lockout after MAX_LOGIN_ATTEMPTS failures (AUTH-04).
    """
    if current_user.is_authenticated:
        return jsonify({"message": "Already logged in."}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    # ---- Sanitise inputs (APP-01) ---- #
    email    = normalise_email(_sanitise_string(data.get("email", "")))
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    # ---- Look up user — use generic error to prevent enumeration (APP-05) ---- #
    GENERIC_FAIL = "Invalid credentials."

    user = User.query.filter_by(email=email).first()

    if user is None:
        # Still run a dummy verify to avoid timing-based user enumeration
        verify_password("dummy", "$2b$12$" + "x" * 53)
        _log_auth_event("LOGIN_UNKNOWN_EMAIL", email=email)
        return jsonify({"error": GENERIC_FAIL}), 401

    # ---- Account lockout check (AUTH-04) ---- #
    if is_account_locked(user.failed_login_attempts, user.lockout_until):
        remaining = get_lockout_remaining_seconds(user.lockout_until)
        _log_auth_event("LOGIN_LOCKED", user_id=user.id, email=email)
        return jsonify({
            "error": f"Account locked. Try again in {remaining} seconds."
        }), 429

    # ---- Verify password (AUTH-02) ---- #
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1

        max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
        if user.failed_login_attempts >= max_attempts:
            user.lockout_until = calculate_lockout_until()
            _log_auth_event(
                "LOGIN_ACCOUNT_LOCKED",
                user_id=user.id, email=email,
                extra=f"attempts={user.failed_login_attempts}",
            )

        db.session.commit()
        _log_auth_event(
            "LOGIN_FAIL",
            user_id=user.id, email=email,
            extra=f"attempts={user.failed_login_attempts}",
        )
        return jsonify({"error": GENERIC_FAIL}), 401

    # ---- Successful login ---- #
    # Reset lockout counters
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    # Issue Flask-Login session (AUTH-05)
    login_user(user, remember=False)

    _log_auth_event("LOGIN_SUCCESS", user_id=user.id, email=email)

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id":        user.id,
            "username":  user.username,
            "role":      user.role,
            "full_name": user.full_name,
        }
    }), 200


# ------------------------------------------------------------------ #
# POST /auth/logout
# ------------------------------------------------------------------ #

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    Invalidate the server-side session (AUTH-07).
    Flask-Login removes the user from the session store.
    """
    user_id = current_user.id
    logout_user()
    session.clear()         # Wipe any residual session data

    _log_auth_event("LOGOUT", user_id=user_id)

    return jsonify({"message": "Logged out successfully."}), 200


# ------------------------------------------------------------------ #
# POST /auth/change-password
# ------------------------------------------------------------------ #

@auth_bp.route("/change-password", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def change_password():
    """
    Allow an authenticated user to change their own password.
    Requires current password confirmation to prevent CSRF abuse.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    current_password = data.get("current_password", "")
    new_password     = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Both current and new passwords are required."}), 400

    # Verify existing password
    if not verify_password(current_password, current_user.password_hash):
        _log_auth_event("PASSWORD_CHANGE_FAIL", user_id=current_user.id)
        return jsonify({"error": "Current password is incorrect."}), 401

    # Validate new password strength (AUTH-03)
    is_strong, pw_errors = validate_password_strength(new_password)
    if not is_strong:
        return jsonify({"errors": {"new_password": pw_errors}}), 422

    # Prevent reuse of current password
    if verify_password(new_password, current_user.password_hash):
        return jsonify({"error": "New password must differ from the current one."}), 422

    # Update hash (AUTH-02)
    current_user.password_hash = hash_password(new_password)
    db.session.commit()

    _log_auth_event("PASSWORD_CHANGE_SUCCESS", user_id=current_user.id)

    return jsonify({"message": "Password updated successfully."}), 200


# ------------------------------------------------------------------ #
# GET /auth/me  — current user info
# ------------------------------------------------------------------ #

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Return the current user's non-sensitive profile data."""
    return jsonify({
        "id":        current_user.id,
        "username":  current_user.username,
        "email":     current_user.email,
        "full_name": current_user.full_name,
        "role":      current_user.role,
    }), 200
