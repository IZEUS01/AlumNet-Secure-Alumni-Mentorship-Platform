"""
routes/mentorship.py
---------------------
Mentorship request endpoints for both students and verified alumni.

Security controls:
    RBAC-02  — Students can only send requests to verified alumni
    RBAC-03  — Unverified alumni cannot receive or respond to requests
    RBAC-04  — Only verified alumni can respond (accept/reject)
    APP-01   — All inputs validated server-side via service layer
    APP-05   — Generic error messages
    APP-06   — All state changes logged
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user

from auth.decorators import role_required, login_required_json
from rbac.roles import Role
from services.mentorship import (
    send_mentorship_request,
    withdraw_mentorship_request,
    get_student_requests,
    get_alumni_requests,
)

mentorship_bp = Blueprint("mentorship", __name__)


# ------------------------------------------------------------------ #
# POST /mentorship/request  — student sends a request
# ------------------------------------------------------------------ #

@mentorship_bp.route("/request", methods=["POST"])
@login_required_json
@role_required(Role.STUDENT)
def create_request():
    """
    Student sends a mentorship request to a verified alumni.
    Service layer enforces: verification check, duplicate prevention,
    capacity check, and input sanitisation (APP-01, RBAC-02, RBAC-03).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body."}), 400

    alumni_id = data.get("alumni_id")
    subject   = data.get("subject", "")
    message   = data.get("message", "")

    if not alumni_id:
        return jsonify({"error": "alumni_id is required."}), 400

    try:
        req = send_mentorship_request(
            student_user_id=current_user.id,
            alumni_id=alumni_id,
            subject=subject,
            message=message,
        )
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    return jsonify({
        "message": "Mentorship request sent.",
        "request_id": req.id,
        "status": req.status,
    }), 201


# ------------------------------------------------------------------ #
# GET /mentorship/my-requests  — student views their own requests
# ------------------------------------------------------------------ #

@mentorship_bp.route("/my-requests", methods=["GET"])
@login_required_json
@role_required(Role.STUDENT)
def my_requests():
    """Return all mentorship requests sent by the current student."""
    status = request.args.get("status", None)
    valid  = {"pending", "accepted", "rejected", "withdrawn", None}
    if status not in valid:
        return jsonify({"error": "Invalid status filter."}), 400

    reqs = get_student_requests(current_user.id, status=status)
    return jsonify({
        "requests": [r.to_student_dict() for r in reqs],
        "count":    len(reqs),
    }), 200


# ------------------------------------------------------------------ #
# POST /mentorship/withdraw/<request_id>  — student withdraws a request
# ------------------------------------------------------------------ #

@mentorship_bp.route("/withdraw/<int:request_id>", methods=["POST"])
@login_required_json
@role_required(Role.STUDENT)
def withdraw_request(request_id):
    """Student withdraws their own pending request."""
    try:
        req = withdraw_mentorship_request(current_user.id, request_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    return jsonify({"message": "Request withdrawn.", "status": req.status}), 200


# ------------------------------------------------------------------ #
# GET /mentorship/inbox  — alumni views incoming requests (RBAC-04)
# ------------------------------------------------------------------ #

@mentorship_bp.route("/inbox", methods=["GET"])
@login_required_json
@role_required(Role.VERIFIED_ALUMNI)
def inbox():
    """
    Verified alumni views their mentorship inbox.
    Unverified alumni are blocked (RBAC-03, RBAC-04).
    """
    status = request.args.get("status", "pending")
    valid  = {"pending", "accepted", "rejected", "withdrawn"}
    if status not in valid:
        return jsonify({"error": "Invalid status filter."}), 400

    reqs = get_alumni_requests(current_user.id, status=status)
    return jsonify({
        "requests": [r.to_alumni_dict() for r in reqs],
        "count":    len(reqs),
    }), 200
