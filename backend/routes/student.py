"""
routes/student.py
-----------------
Student-facing endpoints: profile management, alumni browsing,
company/industry search, and connection requests.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from extensions import db          # ✅ FIXED: was "from app import db"
from models.student import Student
from models.alumni import Alumni
from models.work_experience import WorkExperience
from models.user import User
from auth.decorators import role_required, login_required_json
from rbac.roles import Role

student_bp = Blueprint("student", __name__)


# ── GET /student/profile ──────────────────────────────────────────────────────

@student_bp.route("/profile", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def get_profile():
    profile = Student.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404
    return jsonify(profile.to_public_dict()), 200


# ── PUT /student/profile ──────────────────────────────────────────────────────

@student_bp.route("/profile", methods=["PUT"])
@login_required_json
@role_required(Role.STUDENT)
def update_profile():
    """Update the current student's profile (whitelisted fields only)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    profile = Student.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = Student(user_id=current_user.id, department="", degree_program="")
        db.session.add(profile)

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
    current_app.logger.info("STUDENT_PROFILE_UPDATED user_id=%s", current_user.id)
    return jsonify({"message": "Profile updated.", "profile": profile.to_public_dict()}), 200


# ── GET /student/alumni  — browse verified alumni ─────────────────────────────

@student_bp.route("/alumni", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def list_alumni():
    """Return paginated list of verified alumni. Supports filters."""
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    department = request.args.get("department", "").strip()[:120]
    industry   = request.args.get("industry",   "").strip()[:120]
    accepting  = request.args.get("accepting_mentees", None)

    query = Alumni.query.filter_by(is_verified=True)

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


# ── GET /student/alumni/search  — search by company or industry ───────────────

@student_bp.route("/alumni/search", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def search_alumni():
    """
    Search verified alumni by company name or industry.

    Searches across:
      1. alumni.current_company / alumni.industry (quick-access fields)
      2. work_experiences.company / work_experiences.industry (full history)

    Returns unique alumni — so if an alumni worked at Jazz twice,
    they appear once.

    Query params:
      ?company=Jazz          — search company name (partial match)
      ?industry=Telecom      — search industry (partial match)
      ?page=1&per_page=20
    """
    company  = request.args.get("company",  "").strip()[:200]
    industry = request.args.get("industry", "").strip()[:120]
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    if not company and not industry:
        return jsonify({"error": "Provide at least one of: company, industry."}), 400

    # Collect matching alumni IDs from both sources
    matched_ids = set()

    # 1. Search work history (covers both past and current jobs)
    work_query = WorkExperience.query.join(
        Alumni, WorkExperience.alumni_id == Alumni.id
    ).join(
        User, Alumni.user_id == User.id
    ).filter(Alumni.is_verified == True)  # noqa: E712

    if company:
        work_query = work_query.filter(
            WorkExperience.company.ilike(f"%{company}%")
        )
    if industry:
        work_query = work_query.filter(
            WorkExperience.industry.ilike(f"%{industry}%")
        )

    for entry in work_query.all():
        matched_ids.add(entry.alumni_id)

    # 2. Also search alumni.current_company / industry fields directly
    alumni_query = Alumni.query.filter(Alumni.is_verified == True)  # noqa: E712
    if company:
        alumni_query = alumni_query.filter(Alumni.current_company.ilike(f"%{company}%"))
    if industry and not company:
        alumni_query = alumni_query.filter(Alumni.industry.ilike(f"%{industry}%"))

    for a in alumni_query.all():
        matched_ids.add(a.id)

    if not matched_ids:
        return jsonify({
            "alumni":   [],
            "total":    0,
            "page":     page,
            "pages":    0,
            "query":    {"company": company, "industry": industry},
        }), 200

    # Paginate the matched IDs
    all_matched = (
        Alumni.query
        .filter(Alumni.id.in_(matched_ids))
        .filter(Alumni.is_verified == True)  # noqa: E712
        .order_by(Alumni.id)
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    # For each alumni, annotate which jobs matched the search
    results = []
    for a in all_matched.items:
        alumni_data = a.to_public_dict()
        # Highlight matching work entries
        matching_jobs = []
        for w in a.work_experiences:
            company_match  = company  and company.lower()  in w.company.lower()
            industry_match = industry and w.industry and industry.lower() in w.industry.lower()
            if company_match or industry_match:
                matching_jobs.append(w.to_dict())
        alumni_data["matching_jobs"] = matching_jobs
        results.append(alumni_data)

    return jsonify({
        "alumni":  results,
        "total":   all_matched.total,
        "page":    all_matched.page,
        "pages":   all_matched.pages,
        "query":   {"company": company, "industry": industry},
    }), 200


# ── GET /student/alumni/<id>  — view single alumni profile ───────────────────

@student_bp.route("/alumni/<int:alumni_id>", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def get_alumni(alumni_id):
    alumni = Alumni.query.filter_by(id=alumni_id, is_verified=True).first()
    if not alumni:
        return jsonify({"error": "Alumni not found."}), 404
    return jsonify(alumni.to_public_dict()), 200


# ── POST /student/connections/request  — send connection request ──────────────

@student_bp.route("/connections/request", methods=["POST"])
@login_required_json
@role_required(Role.STUDENT)
def send_connection_request():
    """Send a connection request to a verified alumni."""
    from models.mentorship import MentorshipRequest

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    alumni_id = data.get("alumni_id")
    subject   = str(data.get("subject", "Connection Request")).strip()[:255]
    message   = str(data.get("message", "")).strip()[:2000]

    if not alumni_id:
        return jsonify({"error": "alumni_id is required."}), 400
    if not message:
        return jsonify({"error": "A message is required."}), 400

    # Verify target alumni exists and is verified
    alumni = Alumni.query.filter_by(id=alumni_id, is_verified=True).first()
    if not alumni:
        return jsonify({"error": "Alumni not found or not verified."}), 404

    # Get student profile
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"error": "Student profile not found."}), 404

    # Prevent duplicate pending requests
    existing = MentorshipRequest.query.filter_by(
        student_id=student.id, alumni_id=alumni_id, status="pending"
    ).first()
    if existing:
        return jsonify({"error": "You already have a pending request to this alumni."}), 409

    req = MentorshipRequest(
        student_id=student.id,
        alumni_id=alumni_id,
        subject=subject,
        message=message,
        status="pending",
    )
    db.session.add(req)
    db.session.commit()

    current_app.logger.info(
        "CONNECTION_REQUEST_SENT student=%s alumni=%s", student.id, alumni_id
    )
    return jsonify({
        "message":    "Connection request sent.",
        "request_id": req.id,
        "status":     req.status,
    }), 201


# ── GET /student/connections/my-requests  — student's sent requests ───────────

@student_bp.route("/connections/my-requests", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def my_connection_requests():
    """Return all connection requests sent by the current student."""
    from models.mentorship import MentorshipRequest

    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"error": "Student profile not found."}), 404

    status = request.args.get("status", None)
    valid  = {"pending", "accepted", "rejected", "withdrawn", None}
    if status not in valid:
        return jsonify({"error": "Invalid status filter."}), 400

    query = MentorshipRequest.query.filter_by(student_id=student.id)
    if status:
        query = query.filter_by(status=status)

    reqs = query.order_by(MentorshipRequest.created_at.desc()).all()
    return jsonify({
        "requests": [r.to_student_dict() for r in reqs],
        "count":    len(reqs),
    }), 200


# ── POST /student/connections/withdraw/<id>  — withdraw a request ─────────────

@student_bp.route("/connections/withdraw/<int:request_id>", methods=["POST"])
@login_required_json
@role_required(Role.STUDENT)
def withdraw_connection(request_id):
    from models.mentorship import MentorshipRequest

    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"error": "Student profile not found."}), 404

    req = MentorshipRequest.query.filter_by(
        id=request_id, student_id=student.id
    ).first()
    if not req:
        return jsonify({"error": "Request not found."}), 404
    if req.status != "pending":
        return jsonify({"error": f"Cannot withdraw a {req.status} request."}), 409

    req.withdraw()
    db.session.commit()
    return jsonify({"message": "Request withdrawn.", "status": req.status}), 200
