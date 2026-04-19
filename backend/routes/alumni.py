"""
routes/alumni.py
----------------
Alumni-facing endpoints: profile management, work history CRUD,
and connection request inbox.
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from extensions import db          # ✅ FIXED: was "from app import db"
from models.alumni import Alumni
from models.work_experience import WorkExperience
from models.user import User
from auth.decorators import role_required, login_required_json
from rbac.roles import Role

alumni_bp = Blueprint("alumni", __name__)


# ── GET /alumni/profile ───────────────────────────────────────────────────────

@alumni_bp.route("/profile", methods=["GET"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def get_profile():
    """Return the current alumni's own full profile."""
    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    data = profile.to_public_dict()
    data["gik_roll_number"] = profile.gik_roll_number
    data["work_email"]      = profile.work_email
    data["github_url"]      = profile.github_url
    data["is_verified"]     = profile.is_verified
    data["account_status"]  = current_user.account_status
    return jsonify(data), 200


# ── PUT /alumni/profile ───────────────────────────────────────────────────────

@alumni_bp.route("/profile", methods=["PUT"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def update_profile():
    """Update professional/academic profile fields (whitelisted only)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    errors = {}

    if "not_currently_working" in data:
        profile.not_currently_working = bool(data["not_currently_working"])
        # Clear current job fields when marked not working
        if profile.not_currently_working:
            profile.current_company   = None
            profile.current_job_title = None

    if "current_company" in data:
        if not profile.not_currently_working:
            profile.current_company = str(data["current_company"]).strip()[:200] or None

    if "current_job_title" in data:
        if not profile.not_currently_working:
            profile.current_job_title = str(data["current_job_title"]).strip()[:150] or None

    if "industry" in data:
        profile.industry = str(data["industry"]).strip()[:120] or None

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
            errors["linkedin_url"] = "Must be a valid LinkedIn URL (https://www.linkedin.com/...)."
        else:
            profile.linkedin_url = url or None

    if "github_url" in data:
        url = str(data["github_url"]).strip()[:300]
        if url and not url.startswith("https://github.com/"):
            errors["github_url"] = "Must be a valid GitHub URL (https://github.com/...)."
        else:
            profile.github_url = url or None

    if "work_email" in data:
        profile.work_email = str(data["work_email"]).strip()[:254] or None

    if "bio" in data:
        profile.bio = str(data["bio"]).strip()[:1000] or None

    if "expertise_areas" in data:
        if isinstance(data["expertise_areas"], list):
            profile.set_expertise_list(
                [str(e).strip()[:50] for e in data["expertise_areas"] if str(e).strip()]
            )
        else:
            errors["expertise_areas"] = "Must be a list of strings."

    if "is_accepting_mentees" in data:
        profile.is_accepting_mentees = bool(data["is_accepting_mentees"])

    if errors:
        return jsonify({"errors": errors}), 422

    profile.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    current_app.logger.info("ALUMNI_PROFILE_UPDATED user_id=%s", current_user.id)
    return jsonify({"message": "Profile updated."}), 200


# ── WORK EXPERIENCE CRUD ──────────────────────────────────────────────────────

# GET /alumni/work-experience  — list all entries
@alumni_bp.route("/work-experience", methods=["GET"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def list_work_experience():
    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404
    return jsonify({
        "work_history": [w.to_dict() for w in profile.work_experiences],
        "count": len(profile.work_experiences),
    }), 200


# POST /alumni/work-experience  — add new entry
@alumni_bp.route("/work-experience", methods=["POST"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def add_work_experience():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    errors = {}
    company   = str(data.get("company", "")).strip()[:200]
    job_title = str(data.get("job_title", "")).strip()[:150]
    industry  = str(data.get("industry", "")).strip()[:120] or None
    description = str(data.get("description", "")).strip()[:1000] or None
    is_current  = bool(data.get("is_current", False))

    if not company:
        errors["company"] = "Company name is required."
    if not job_title:
        errors["job_title"] = "Job title is required."

    try:
        start_year = int(data.get("start_year", 0))
        if not (1950 <= start_year <= datetime.now().year):
            errors["start_year"] = "Enter a valid start year."
    except (ValueError, TypeError):
        errors["start_year"] = "Start year must be a number."
        start_year = 0

    end_year = None
    if not is_current:
        try:
            end_year = int(data.get("end_year", 0))
            if not (1950 <= end_year <= datetime.now().year):
                errors["end_year"] = "Enter a valid end year."
            elif start_year and end_year < start_year:
                errors["end_year"] = "End year cannot be before start year."
        except (ValueError, TypeError):
            errors["end_year"] = "End year must be a number."

    if errors:
        return jsonify({"errors": errors}), 422

    # If marking as current, unset any existing current entries
    if is_current:
        for existing in profile.work_experiences:
            if existing.is_current:
                existing.is_current = False
                existing.end_year = start_year  # approximate

    entry = WorkExperience(
        alumni_id=profile.id,
        company=company,
        job_title=job_title,
        industry=industry,
        description=description,
        start_year=start_year,
        end_year=end_year,
        is_current=is_current,
    )
    # Also update alumni's current_company/title for quick access
    if is_current:
        profile.current_company   = company
        profile.current_job_title = job_title
        if industry:
            profile.industry = industry
        profile.not_currently_working = False

    db.session.add(entry)
    db.session.commit()

    current_app.logger.info(
        "ALUMNI_WORK_ADDED user_id=%s company=%s", current_user.id, company
    )
    return jsonify({"message": "Work experience added.", "entry": entry.to_dict()}), 201


# PUT /alumni/work-experience/<entry_id>  — update an entry
@alumni_bp.route("/work-experience/<int:entry_id>", methods=["PUT"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def update_work_experience(entry_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    entry = WorkExperience.query.filter_by(id=entry_id, alumni_id=profile.id).first()
    if not entry:
        return jsonify({"error": "Work experience entry not found."}), 404

    errors = {}

    if "company" in data:
        val = str(data["company"]).strip()[:200]
        if not val:
            errors["company"] = "Company name cannot be empty."
        else:
            entry.company = val

    if "job_title" in data:
        val = str(data["job_title"]).strip()[:150]
        if not val:
            errors["job_title"] = "Job title cannot be empty."
        else:
            entry.job_title = val

    if "industry" in data:
        entry.industry = str(data["industry"]).strip()[:120] or None

    if "description" in data:
        entry.description = str(data["description"]).strip()[:1000] or None

    if "is_current" in data:
        entry.is_current = bool(data["is_current"])
        if entry.is_current:
            entry.end_year = None
            # Unset other current entries
            for other in profile.work_experiences:
                if other.id != entry.id and other.is_current:
                    other.is_current = False

    if "start_year" in data:
        try:
            sy = int(data["start_year"])
            if not (1950 <= sy <= datetime.now().year):
                errors["start_year"] = "Enter a valid start year."
            else:
                entry.start_year = sy
        except (ValueError, TypeError):
            errors["start_year"] = "Start year must be a number."

    if "end_year" in data and not entry.is_current:
        try:
            ey = int(data["end_year"])
            if not (1950 <= ey <= datetime.now().year):
                errors["end_year"] = "Enter a valid end year."
            else:
                entry.end_year = ey
        except (ValueError, TypeError):
            errors["end_year"] = "End year must be a number."

    if errors:
        return jsonify({"errors": errors}), 422

    # Sync current company on alumni profile if this is the current job
    if entry.is_current:
        profile.current_company   = entry.company
        profile.current_job_title = entry.job_title
        profile.not_currently_working = False

    db.session.commit()
    return jsonify({"message": "Work experience updated.", "entry": entry.to_dict()}), 200


# DELETE /alumni/work-experience/<entry_id>  — remove an entry
@alumni_bp.route("/work-experience/<int:entry_id>", methods=["DELETE"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def delete_work_experience(entry_id):
    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    entry = WorkExperience.query.filter_by(id=entry_id, alumni_id=profile.id).first()
    if not entry:
        return jsonify({"error": "Work experience entry not found."}), 404

    # If deleting the current job, clear alumni's current_company
    if entry.is_current:
        profile.current_company   = None
        profile.current_job_title = None

    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Work experience deleted."}), 200


# ── CONNECTION REQUEST INBOX ──────────────────────────────────────────────────

@alumni_bp.route("/connections/requests", methods=["GET"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def list_connection_requests():
    """Verified alumni views incoming connection requests from students."""
    from models.mentorship import MentorshipRequest

    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Alumni profile not found."}), 404

    status_filter = request.args.get("status", "pending")
    if status_filter not in {"pending", "accepted", "rejected", "withdrawn"}:
        return jsonify({"error": "Invalid status filter."}), 400

    reqs = MentorshipRequest.query.filter_by(
        alumni_id=profile.id, status=status_filter
    ).order_by(MentorshipRequest.created_at.desc()).all()

    return jsonify({
        "requests": [r.to_alumni_dict() for r in reqs],
        "count":    len(reqs),
    }), 200


@alumni_bp.route("/connections/requests/<int:request_id>/respond", methods=["POST"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def respond_to_connection(request_id):
    """Accept or reject a student connection request."""
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

    req = MentorshipRequest.query.filter_by(id=request_id, alumni_id=profile.id).first()
    if not req:
        return jsonify({"error": "Request not found."}), 404

    if req.status != "pending":
        return jsonify({"error": f"Request is already {req.status}."}), 409

    if action == "accept":
        req.accept(response_note=response_note)
    else:
        req.reject(response_note=response_note)

    db.session.commit()
    return jsonify({"message": f"Request {action}ed.", "status": req.status}), 200


# ── VERIFICATION STATUS ───────────────────────────────────────────────────────

@alumni_bp.route("/verification/status", methods=["GET"])
@login_required_json
@role_required(Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI)
def verification_status():
    profile = Alumni.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    return jsonify({
        "account_status":    current_user.account_status,
        "is_verified":       profile.is_verified,
        "verified_at":       profile.verified_at.isoformat() if profile.verified_at else None,
        "rejection_reason":  profile.rejection_reason or current_user.rejection_reason,
        "documents":         [doc.to_alumni_dict() for doc in profile.verification_documents],
    }), 200

    # Keep legacy mentorship endpoint aliases
@alumni_bp.route("/mentorship/requests", methods=["GET"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def list_mentorship_requests():
    return list_connection_requests()

@alumni_bp.route("/mentorship/requests/<int:request_id>/respond", methods=["POST"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def respond_to_request(request_id):
    return respond_to_connection(request_id)
