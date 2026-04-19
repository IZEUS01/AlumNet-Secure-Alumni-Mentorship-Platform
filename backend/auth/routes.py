"""
auth/routes.py
--------------
Authentication endpoints.

  POST /auth/register        — create account (pending admin approval)
  POST /auth/login           — authenticate (blocked if not approved)
  POST /auth/logout          — invalidate session
  POST /auth/change-password — change own password
  GET  /auth/me              — current user info
"""

import re
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, session
from flask_login import login_user, logout_user, current_user, login_required

from extensions import db, limiter
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


# ── helpers ──────────────────────────────────────────────────────────────────

def _clean(val, max_len=255):
    return val.strip()[:max_len] if val else ""

def _valid_email(email):
    return bool(re.match(r'^[\w\.\+\-]+@[\w\.\-]+\.[a-zA-Z]{2,}$', email))

def _log(event, user_id=None, email=None, extra=None):
    current_app.logger.info(
        "AUTH event=%s user_id=%s email=%s ip=%s extra=%s",
        event, user_id, email, request.remote_addr, extra,
    )


# ── POST /auth/register ──────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    email      = _clean(data.get("email", ""))
    username   = _clean(data.get("username", ""))
    password   = data.get("password", "")
    full_name  = _clean(data.get("full_name", ""))
    role_input = _clean(data.get("role", "student")).lower()

    # Role-specific required fields
    department      = _clean(data.get("department", ""), 120)
    graduation_year = data.get("graduation_year")

    # Student-only fields
    degree_program   = _clean(data.get("degree_program", ""), 120)
    current_semester = data.get("current_semester")

    # Alumni-only fields
    gik_roll_number = _clean(data.get("gik_roll_number", ""), 20)

    # ── Validate common fields ──
    errors = {}
    if not email or not _valid_email(email):
        errors["email"] = "A valid email address is required."
    if not username or len(username) < 3:
        errors["username"] = "Username must be at least 3 characters."
    if not re.match(r"^[a-zA-Z0-9_.]{3,80}$", username):
        errors["username"] = "Only letters, numbers, _ and . allowed."
    if not full_name:
        errors["full_name"] = "Full name is required."
    if role_input not in ("student", "alumni"):
        errors["role"] = "Role must be 'student' or 'alumni'."
    if not department:
        errors["department"] = "Department is required."
    if not graduation_year:
        errors["graduation_year"] = "Graduation year is required."
    else:
        try:
            graduation_year = int(graduation_year)
            if not (1990 <= graduation_year <= 2040):
                errors["graduation_year"] = "Enter a valid graduation year."
        except (ValueError, TypeError):
            errors["graduation_year"] = "Graduation year must be a number."

    if not password:
        errors["password"] = "Password is required."
    else:
        ok, pw_errors = validate_password_strength(password)
        if not ok:
            errors["password"] = pw_errors

    if errors:
        return jsonify({"errors": errors}), 422

    email = normalise_email(email)

    # Duplicate check — generic message prevents user enumeration (APP-05)
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Registration failed. Please try again."}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Registration failed. Please try again."}), 409

    assigned_role = Role.UNVERIFIED_ALUMNI if role_input == "alumni" else Role.STUDENT

    # ── Create User ── account_status defaults to 'pending'
    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=assigned_role,
        email_verified=True,
        account_status="pending",   # Must be approved by admin before login
    )
    db.session.add(user)
    db.session.flush()  # get user.id before creating profile

    # ── Auto-create role profile ──
    if role_input == "student":
        from models.student import Student
        profile = Student(
            user_id=user.id,
            department=department,
            degree_program=degree_program or "Not specified",
            graduation_year=graduation_year,
        )
        if current_semester:
            try:
                sem = int(current_semester)
                if 1 <= sem <= 8:
                    profile.current_semester = sem
            except (ValueError, TypeError):
                pass
        db.session.add(profile)

    else:  # alumni
        from models.alumni import Alumni
        profile = Alumni(
            user_id=user.id,
            department=department,
            graduation_year=graduation_year,
            gik_roll_number=gik_roll_number or None,
            is_verified=False,
        )
        db.session.add(profile)

    db.session.commit()

    _log("REGISTER_SUCCESS", user_id=user.id, email=email)

    return jsonify({
        "message": (
            "Account created successfully. "
            "Please wait for admin approval before logging in."
        ),
        "role": assigned_role,
        "account_status": "pending",
    }), 201


# ── POST /auth/login ─────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per minute;100 per hour")
def login():
    if current_user.is_authenticated:
        return jsonify({"message": "Already logged in."}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    email    = normalise_email(_clean(data.get("email", "")))
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    FAIL = "Invalid email or password."

    user = User.query.filter_by(email=email).first()
    if user is None:
        verify_password("dummy", "$2b$12$" + "x" * 53)  # Constant-time dummy
        _log("LOGIN_UNKNOWN_EMAIL", email=email)
        return jsonify({"error": FAIL}), 401

    # ── ✅ Admin approval gate ──
    if user.account_status == "pending":
        _log("LOGIN_BLOCKED_PENDING", user_id=user.id, email=email)
        return jsonify({
            "error": "Your account is pending admin approval. Please check back later."
        }), 403

    if user.account_status == "rejected":
        _log("LOGIN_BLOCKED_REJECTED", user_id=user.id, email=email)
        reason = user.rejection_reason or "No reason provided."
        return jsonify({
            "error": f"Your account registration was rejected. Reason: {reason}"
        }), 403

    # ── Active check ──
    if not user.is_active:
        return jsonify({"error": "Account has been deactivated."}), 403

    # Lockout check (AUTH-04)
    if is_account_locked(user.failed_login_attempts, user.lockout_until):
        remaining = get_lockout_remaining_seconds(user.lockout_until)
        return jsonify({"error": f"Account locked. Try again in {remaining}s."}), 429

    # Password check (AUTH-02)
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        max_att = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
        if user.failed_login_attempts >= max_att:
            user.lockout_until = calculate_lockout_until()
        db.session.commit()
        _log("LOGIN_FAIL", user_id=user.id, email=email,
             extra=f"attempts={user.failed_login_attempts}")
        return jsonify({"error": FAIL}), 401

    # ── Success ──
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    login_user(user, remember=False)
    _log("LOGIN_SUCCESS", user_id=user.id, email=email)

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id":             user.id,
            "username":       user.username,
            "role":           user.role,
            "full_name":      user.full_name,
            "account_status": user.account_status,
        },
    }), 200


# ── POST /auth/logout ────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    uid = current_user.id
    logout_user()
    session.clear()
    _log("LOGOUT", user_id=uid)
    return jsonify({"message": "Logged out."}), 200


# ── POST /auth/change-password ───────────────────────────────────────────────

@auth_bp.route("/change-password", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def change_password():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    cur = data.get("current_password", "")
    new = data.get("new_password", "")

    if not cur or not new:
        return jsonify({"error": "Both passwords are required."}), 400
    if not verify_password(cur, current_user.password_hash):
        return jsonify({"error": "Current password is incorrect."}), 401

    ok, errs = validate_password_strength(new)
    if not ok:
        return jsonify({"errors": {"new_password": errs}}), 422
    if verify_password(new, current_user.password_hash):
        return jsonify({"error": "New password must differ from the current one."}), 422

    current_user.password_hash = hash_password(new)
    db.session.commit()
    _log("PASSWORD_CHANGE_SUCCESS", user_id=current_user.id)
    return jsonify({"message": "Password updated."}), 200


# ── GET /auth/me ─────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({
        "id":             current_user.id,
        "username":       current_user.username,
        "email":          current_user.email,
        "full_name":      current_user.full_name,
        "role":           current_user.role,
        "account_status": current_user.account_status,
    }), 200
