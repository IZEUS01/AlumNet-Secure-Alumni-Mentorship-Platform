"""
routes/student.py
-----------------
Student-facing endpoints: profile management and alumni browsing.

Security controls:
    RBAC-01  — All routes require authentication + student role
    RBAC-02  — Students may only browse VERIFIED alumni profiles
    DATA-01  — Sensitive PII not exposed in alumni listing
    APP-01   — All inputs validated server-side
    APP-05   — Generic error messages
    APP-06   — Actions logged
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from app import db
from models.student import Student
from models.alumni import Alumni
from auth.decorators import role_required, login_required_json
from rbac.roles import Role

student_bp = Blueprint("student", __name__)


# ------------------------------------------------------------------ #
# GET /student/profile  — view own profile
# ------------------------------------------------------------------ #

@student_bp.route("/profile", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def get_profile():
    """Return the current student's profile."""
    profile = Student.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404
    return jsonify(profile.to_public_dict()), 200


# ------------------------------------------------------------------ #
# PUT /student/profile  — update own profile
# ------------------------------------------------------------------ #

@student_bp.route("/profile", methods=["PUT"])
@login_required_json
@role_required(Role.STUDENT)
def update_profile():
    """
    Update the current student's academic info and mentorship preferences.
    Only whitelisted fields are accepted (APP-01).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    profile = Student.query.filter_by(user_id=current_user.id).first()
    if not profile:
        # Auto-create profile on first update
        profile = Student(user_id=current_user.id,
                          department="", degree_program="")
        db.session.add(profile)

    # Whitelist of editable fields (APP-01 — no mass assignment)
    ALLOWED_FIELDS = {
        "department", "degree_program", "graduation_year",
        "current_semester", "interests", "bio", "profile_visible",
    }

    errors = {}

    if "department" in data:
        val = str(data["department"]).strip()[:120]
        if not val:
            errors["department"] = "Department cannot be empty."
        else:
            profile.department = val

    if "degree_program" in data:
        val = str(data["degree_program"]).strip()[:120]
        if not val:
            errors["degree_program"] = "Degree program cannot be empty."
        else:
            profile.degree_program = val

    if "graduation_year" in data:
        try:
            yr = int(data["graduation_year"])
            if not (2000 <= yr <= 2040):
                errors["graduation_year"] = "Enter a valid graduation year."
            else:
                profile.graduation_year = yr
        except (ValueError, TypeError):
            errors["graduation_year"] = "Graduation year must be a number."

    if "current_semester" in data:
        try:
            sem = int(data["current_semester"])
            if not (1 <= sem <= 8):
                errors["current_semester"] = "Semester must be between 1 and 8."
            else:
                profile.current_semester = sem
        except (ValueError, TypeError):
            errors["current_semester"] = "Semester must be a number."

    if "interests" in data:
        if isinstance(data["interests"], list):
            profile.set_interests_list(
                [str(i).strip()[:50] for i in data["interests"] if str(i).strip()]
            )
        else:
            errors["interests"] = "Interests must be a list of strings."

    if "bio" in data:
        profile.bio = str(data["bio"]).strip()[:500]

    if "profile_visible" in data:
        profile.profile_visible = bool(data["profile_visible"])

    if errors:
        return jsonify({"errors": errors}), 422

    db.session.commit()

    current_app.logger.info(
        "STUDENT_PROFILE_UPDATED user_id=%s", current_user.id
    )
    return jsonify({"message": "Profile updated.", "profile": profile.to_public_dict()}), 200


# ------------------------------------------------------------------ #
# GET /student/alumni  — browse verified alumni (RBAC-02)
# ------------------------------------------------------------------ #

@student_bp.route("/alumni", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def list_alumni():
    """
    Return paginated list of verified alumni available for mentorship.
    Only VERIFIED alumni are shown (RBAC-02).
    Public dict used — no PII exposed (DATA-01).
    """
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    # Optional filters
    department = request.args.get("department", "").strip()[:120]
    industry   = request.args.get("industry",   "").strip()[:120]
    accepting  = request.args.get("accepting_mentees", None)

    query = Alumni.query.filter_by(is_verified=True)  # RBAC-02: verified only

    if department:
        query = query.filter(Alumni.department.ilike(f"%{department}%"))
    if industry:
        query = query.filter(Alumni.industry.ilike(f"%{industry}%"))
    if accepting is not None:
        query = query.filter_by(is_accepting_mentees=(accepting.lower() == "true"))

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "alumni":   [a.to_public_dict() for a in paginated.items],
        "total":    paginated.total,
        "page":     paginated.page,
        "pages":    paginated.pages,
        "per_page": per_page,
    }), 200


# ------------------------------------------------------------------ #
# GET /student/alumni/<alumni_id>  — view a single verified alumni
# ------------------------------------------------------------------ #

@student_bp.route("/alumni/<int:alumni_id>", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def get_alumni(alumni_id):
    """
    Return a single verified alumni's public profile.
    Returns 404 for unverified alumni — avoids information leakage (APP-05).
    """
    alumni = Alumni.query.filter_by(id=alumni_id, is_verified=True).first()
    if not alumni:
        return jsonify({"error": "Alumni not found."}), 404
    return jsonify(alumni.to_public_dict()), 200
