"""
routes/admin.py
---------------
Administrator endpoints: alumni verification, user management,
audit log access.

Security controls:
    RBAC-05  — Every route is admin-only
    RBAC-06  — Role validated server-side via admin_required decorator
    DATA-01  — PII only visible to admins where needed
    APP-05   — Generic error messages
    APP-06   — All admin actions logged with admin user_id
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from app import db
from models.alumni import Alumni
from models.user import User
from models.admin import Admin
from auth.decorators import admin_required
from rbac.roles import Role

admin_bp = Blueprint("admin", __name__)


# ------------------------------------------------------------------ #
# GET /admin/alumni/pending  — list alumni awaiting verification
# ------------------------------------------------------------------ #

@admin_bp.route("/alumni/pending", methods=["GET"])
@admin_required
def list_pending_alumni():
    """
    Return all alumni with unverified_alumni role pending review (RBAC-05).
    Full admin dict exposes PII — accessible to admins only.
    """
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    paginated = (
        Alumni.query
        .join(User, Alumni.user_id == User.id)
        .filter(User.role == Role.UNVERIFIED_ALUMNI)
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "alumni":   [a.to_admin_dict() for a in paginated.items],
        "total":    paginated.total,
        "page":     paginated.page,
        "pages":    paginated.pages,
    }), 200


# ------------------------------------------------------------------ #
# POST /admin/alumni/<alumni_id>/verify  — approve verification
# ------------------------------------------------------------------ #

@admin_bp.route("/alumni/<int:alumni_id>/verify", methods=["POST"])
@admin_required
def verify_alumni(alumni_id):
    """
    Approve an alumni's verification.
    Elevates User.role from unverified_alumni → verified_alumni (RBAC-05).
    """
    alumni = Alumni.query.get(alumni_id)
    if not alumni:
        return jsonify({"error": "Alumni not found."}), 404

    user = User.query.get(alumni.user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.VERIFIED_ALUMNI:
        return jsonify({"message": "Alumni is already verified."}), 200

    # Perform verification
    alumni.is_verified   = True
    alumni.verified_at   = datetime.now(timezone.utc)
    alumni.verified_by   = current_user.id
    alumni.rejection_reason = None
    user.role            = Role.VERIFIED_ALUMNI

    # Update admin action counters (APP-06)
    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    if admin_profile:
        admin_profile.alumni_verified_count += 1
        admin_profile.record_action()

    db.session.commit()

    current_app.logger.info(
        "ADMIN_VERIFY_ALUMNI admin_id=%s alumni_id=%s", current_user.id, alumni_id
    )
    return jsonify({"message": "Alumni verified successfully.", "alumni_id": alumni_id}), 200


# ------------------------------------------------------------------ #
# POST /admin/alumni/<alumni_id>/reject  — reject verification
# ------------------------------------------------------------------ #

@admin_bp.route("/alumni/<int:alumni_id>/reject", methods=["POST"])
@admin_required
def reject_alumni(alumni_id):
    """
    Reject an alumni's verification request with a reason (RBAC-05).
    User remains as unverified_alumni.
    """
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "")).strip()[:500]

    if not reason:
        return jsonify({"error": "A rejection reason is required."}), 400

    alumni = Alumni.query.get(alumni_id)
    if not alumni:
        return jsonify({"error": "Alumni not found."}), 404

    alumni.is_verified      = False
    alumni.rejection_reason = reason

    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    if admin_profile:
        admin_profile.alumni_rejected_count += 1
        admin_profile.record_action()

    db.session.commit()

    current_app.logger.info(
        "ADMIN_REJECT_ALUMNI admin_id=%s alumni_id=%s reason=%s",
        current_user.id, alumni_id, reason,
    )
    return jsonify({"message": "Alumni verification rejected.", "alumni_id": alumni_id}), 200


# ------------------------------------------------------------------ #
# GET /admin/users  — list all users
# ------------------------------------------------------------------ #

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """Return paginated list of all users (RBAC-05)."""
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    role_filter = request.args.get("role", "").strip()

    query = User.query
    if role_filter and role_filter in Role.ALL:
        query = query.filter_by(role=role_filter)

    paginated = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users = [
        {
            "id":         u.id,
            "username":   u.username,
            "email":      u.email,
            "full_name":  u.full_name,
            "role":       u.role,
            "is_active":  u.is_active,
            "created_at": u.created_at.isoformat(),
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in paginated.items
    ]

    return jsonify({
        "users": users,
        "total": paginated.total,
        "page":  paginated.page,
        "pages": paginated.pages,
    }), 200


# ------------------------------------------------------------------ #
# POST /admin/users/<user_id>/deactivate  — deactivate a user account
# ------------------------------------------------------------------ #

@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_user(user_id):
    """
    Deactivate a user account (soft delete).
    Admins cannot deactivate themselves or other admins (RBAC-05).
    """
    if user_id == current_user.id:
        return jsonify({"error": "You cannot deactivate your own account."}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.ADMIN:
        return jsonify({"error": "Admin accounts cannot be deactivated here."}), 403

    if not user.is_active:
        return jsonify({"message": "User is already deactivated."}), 200

    user.is_active = False

    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    if admin_profile:
        admin_profile.users_deactivated_count += 1
        admin_profile.record_action()

    db.session.commit()

    current_app.logger.warning(
        "ADMIN_DEACTIVATE_USER admin_id=%s target_user_id=%s", current_user.id, user_id
    )
    return jsonify({"message": "User deactivated.", "user_id": user_id}), 200


# ------------------------------------------------------------------ #
# GET /admin/stats  — dashboard summary counts
# ------------------------------------------------------------------ #

@admin_bp.route("/stats", methods=["GET"])
@admin_required
def stats():
    """Return high-level user/verification stats for the admin dashboard."""
    total_users         = User.query.count()
    total_students      = User.query.filter_by(role=Role.STUDENT).count()
    total_verified      = User.query.filter_by(role=Role.VERIFIED_ALUMNI).count()
    total_unverified    = User.query.filter_by(role=Role.UNVERIFIED_ALUMNI).count()

    return jsonify({
        "total_users":             total_users,
        "total_students":          total_students,
        "total_verified_alumni":   total_verified,
        "total_unverified_alumni": total_unverified,
    }), 200
