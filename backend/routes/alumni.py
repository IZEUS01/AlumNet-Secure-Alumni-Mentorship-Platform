"""
routes/alumni.py
----------------
Alumni-facing endpoints: profile management, mentorship inbox,
and verification document upload.

Security controls:
    RBAC-03  — Unverified alumni cannot access student data or mentorship
    RBAC-04  — Only verified alumni can respond to mentorship requests
    DATA-01  — PII not exposed beyond what the role needs
    DATA-02  — File type validation delegated to file_upload service
    DATA-03  — File size enforced by MAX_CONTENT_LENGTH
    DATA-04  — Files stored outside public directory
    APP-01   — All inputs validated server-side
    APP-05   — Generic error messages
    APP-06   — Actions logged
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from app import db
from models.alumni import Alumni
from models.user import User
from auth.decorators import role_required, login_required_json
from rbac.roles import Role

alumni_bp = Blueprint("alumni", __name__)


# ------------------------------------------------------------------ #
# GET /alumni/profile  — view own profile
# ------------------------------------------------------------------ #

@alumni_bp.route("/profile", methods=["GET"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def get_profile():
    """Return the current alumni's own full profile."""
    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    # Use admin dict for own view — includes PII the user themselves provided
    data = profile.to_public_dict()
    data["gik_roll_number"] = profile.gik_roll_number
    data["is_verified"]     = profile.is_verified
    return jsonify(data), 200


# ------------------------------------------------------------------ #
# PUT /alumni/profile  — update own profile
# ------------------------------------------------------------------ #

@alumni_bp.route("/profile", methods=["PUT"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def update_profile():
    """
    Update professional/academic profile fields.
    Whitelisted fields only — no mass assignment (APP-01).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    errors = {}

    if "current_company" in data:
        profile.current_company = str(data["current_company"]).strip()[:200]

    if "current_job_title" in data:
        profile.current_job_title = str(data["current_job_title"]).strip()[:150]

    if "industry" in data:
        profile.industry = str(data["industry"]).strip()[:120]

    if "years_of_experience" in data:
        try:
            yoe = int(data["years_of_experience"])
            if not (0 <= yoe <= 60):
                errors["years_of_experience"] = "Enter a valid number of years."
            else:
                profile.years_of_experience = yoe
        except (ValueError, TypeError):
            errors["years_of_experience"] = "Must be a number."

    if "linkedin_url" in data:
        url = str(data["linkedin_url"]).strip()[:300]
        if url and not url.startswith("https://www.linkedin.com/"):
            errors["linkedin_url"] = "Must be a valid LinkedIn URL."
        else:
            profile.linkedin_url = url or None

    if "bio" in data:
        profile.bio = str(data["bio"]).strip()[:1000]

    if "expertise_areas" in data:
        if isinstance(data["expertise_areas"], list):
            profile.set_expertise_list(
                [str(e).strip()[:50] for e in data["expertise_areas"] if str(e).strip()]
            )
        else:
            errors["expertise_areas"] = "Must be a list of strings."

    if "is_accepting_mentees" in data:
        profile.is_accepting_mentees = bool(data["is_accepting_mentees"])

    if "max_mentees" in data:
        try:
            m = int(data["max_mentees"])
            if not (1 <= m <= 10):
                errors["max_mentees"] = "Max mentees must be between 1 and 10."
            else:
                profile.max_mentees = m
        except (ValueError, TypeError):
            errors["max_mentees"] = "Must be a number."

    if errors:
        return jsonify({"errors": errors}), 422

    profile.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    current_app.logger.info(
        "ALUMNI_PROFILE_UPDATED user_id=%s", current_user.id
    )
    return jsonify({"message": "Profile updated."}), 200


# ------------------------------------------------------------------ #
# GET /alumni/mentorship/requests  — view incoming requests
# Verified alumni only (RBAC-04)
# ------------------------------------------------------------------ #

@alumni_bp.route("/mentorship/requests", methods=["GET"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def list_mentorship_requests():
    """
    Return pending mentorship requests addressed to the current alumni.
    Only VERIFIED alumni can see these (RBAC-04, RBAC-03).
    """
    from models.mentorship import MentorshipRequest

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Alumni profile not found."}), 404

    status_filter = request.args.get("status", "pending")
    valid_statuses = {"pending", "accepted", "rejected", "withdrawn"}
    if status_filter not in valid_statuses:
        return jsonify({"error": "Invalid status filter."}), 400

    requests_qs = MentorshipRequest.query.filter_by(
        alumni_id=profile.id, status=status_filter
    ).order_by(MentorshipRequest.created_at.desc()).all()

    return jsonify({
        "requests": [r.to_alumni_dict() for r in requests_qs],
        "count":    len(requests_qs),
    }), 200


# ------------------------------------------------------------------ #
# POST /alumni/mentorship/requests/<request_id>/respond
# ------------------------------------------------------------------ #

@alumni_bp.route("/mentorship/requests/<int:request_id>/respond", methods=["POST"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def respond_to_request(request_id):
    """
    Accept or reject a mentorship request (RBAC-04).
    Alumni can only respond to requests addressed to themselves.
    """
    from models.mentorship import MentorshipRequest

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    action = str(data.get("action", "")).strip().lower()
    if action not in ("accept", "reject"):
        return jsonify({"error": "Action must be 'accept' or 'reject'."}), 400

    response_note = str(data.get("response_note", "")).strip()[:500] or None

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Alumni profile not found."}), 404

    # Ensure this request belongs to the current alumni (RBAC — no IDOR)
    req = MentorshipRequest.query.filter_by(
        id=request_id, alumni_id=profile.id
    ).first()
    if not req:
        return jsonify({"error": "Request not found."}), 404

    if req.status != "pending":
        return jsonify({"error": f"Request is already {req.status}."}), 409

    if action == "accept":
        req.accept(response_note=response_note)
        current_app.logger.info(
            "MENTORSHIP_ACCEPTED alumni_id=%s request_id=%s", profile.id, request_id
        )
    else:
        req.reject(response_note=response_note)
        current_app.logger.info(
            "MENTORSHIP_REJECTED alumni_id=%s request_id=%s", profile.id, request_id
        )

    db.session.commit()
    return jsonify({"message": f"Request {action}ed.", "status": req.status}), 200


# ------------------------------------------------------------------ #
# GET /alumni/verification/status  — check own verification status
# ------------------------------------------------------------------ #

@alumni_bp.route("/verification/status", methods=["GET"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def verification_status():
    """Return the current alumni's verification status and document summary."""
    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    documents = [doc.to_alumni_dict() for doc in profile.verification_documents]

    return jsonify({
        "is_verified":       profile.is_verified,
        "verified_at":       profile.verified_at.isoformat() if profile.verified_at else None,
        "rejection_reason":  profile.rejection_reason,
        "documents":         documents,
        "document_count":    len(documents),
    }), 200
