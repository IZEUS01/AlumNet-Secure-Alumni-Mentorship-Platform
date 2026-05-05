"""
routes/admin.py
---------------
Administrator endpoints: user approval/rejection, alumni verification,
user management, and dashboard stats.

All routes require admin role (RBAC-05).
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user

from extensions import db
from models.alumni import Alumni
from models.student import Student
from models.user import User
from models.admin import Admin
from auth.decorators import admin_required
from rbac.roles import Role

admin_bp = Blueprint("admin", __name__)


# ── GET /admin/stats ──────────────────────────────────────────────────────────

@admin_bp.route("/stats", methods=["GET"])
@admin_required
def stats():
    """Dashboard summary counts."""
    return jsonify({
        "total_users":             User.query.count(),
        "pending_approval":        User.query.filter_by(account_status="pending").count(),
        "total_students":          User.query.filter_by(role=Role.STUDENT).count(),
        "total_verified_alumni":   User.query.filter_by(role=Role.VERIFIED_ALUMNI).count(),
        "total_unverified_alumni": User.query.filter_by(role=Role.UNVERIFIED_ALUMNI).count(),
    }), 200


# ── GET /admin/pending ────────────────────────────────────────────────────────

@admin_bp.route("/pending", methods=["GET"])
@admin_required
def list_pending_users():
    """Return all users with account_status='pending'."""
    page        = request.args.get("page", 1, type=int)
    per_page    = min(request.args.get("per_page", 20, type=int), 50)
    role_filter = request.args.get("role", "").strip()

    query = User.query.filter_by(account_status="pending")
    if role_filter in (Role.STUDENT, Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI):
        query = query.filter_by(role=role_filter)

    paginated = query.order_by(User.created_at.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users_data = []
    for u in paginated.items:
        entry = {
            "id":         u.id,
            "username":   u.username,
            "email":      u.email,
            "full_name":  u.full_name,
            "role":       u.role,
            "created_at": u.created_at.isoformat(),
        }
        if u.role == Role.STUDENT and u.student_profile:
            p = u.student_profile
            entry["department"]      = p.department
            entry["degree_program"]  = p.degree_program
            entry["graduation_year"] = p.graduation_year
        elif u.role in (Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI) and u.alumni_profile:
            p = u.alumni_profile
            entry["department"]      = p.department
            entry["graduation_year"] = p.graduation_year
            entry["gik_roll_number"] = p.gik_roll_number
        users_data.append(entry)

    return jsonify({
        "users":  users_data,
        "total":  paginated.total,
        "page":   paginated.page,
        "pages":  paginated.pages,
    }), 200


# ── POST /admin/users/<user_id>/approve ──────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/approve", methods=["POST"])
@admin_required
def approve_user(user_id):
    """
    Approve a pending user account (student or alumni).
    - Students: account_status → approved, they can now log in.
    - Alumni: account_status → approved AND is_verified → True, role → verified_alumni.
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.account_status == "approved":
        return jsonify({"message": "User is already approved."}), 200

    user.account_status   = "approved"
    user.is_active        = True
    user.rejection_reason = None

    # For alumni, also flip verification flag
    if user.role in (Role.UNVERIFIED_ALUMNI, Role.VERIFIED_ALUMNI):
        user.role = Role.VERIFIED_ALUMNI
        if user.alumni_profile:
            user.alumni_profile.is_verified      = True
            user.alumni_profile.verified_at      = datetime.now(timezone.utc)
            user.alumni_profile.verified_by      = current_user.id
            user.alumni_profile.rejection_reason = None

    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    if admin_profile:
        if user.role == Role.VERIFIED_ALUMNI:
            admin_profile.alumni_verified_count += 1
        admin_profile.record_action()

    db.session.commit()

    current_app.logger.info(
        "ADMIN_APPROVE_USER admin_id=%s target_user_id=%s role=%s",
        current_user.id, user_id, user.role,
    )
    return jsonify({
        "message": f"User '{user.username}' approved successfully.",
        "user_id": user_id,
        "role":    user.role,
    }), 200


# ── POST /admin/users/<user_id>/reject ───────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/reject", methods=["POST"])
@admin_required
def reject_user(user_id):
    """Reject a pending user account with a reason."""
    data   = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "")).strip()[:500]
    if not reason:
        return jsonify({"error": "A rejection reason is required."}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.ADMIN:
        return jsonify({"error": "Admin accounts cannot be rejected."}), 403

    user.account_status   = "rejected"
    user.rejection_reason = reason

    if user.alumni_profile:
        user.alumni_profile.is_verified      = False
        user.alumni_profile.rejection_reason = reason

    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    if admin_profile:
        admin_profile.alumni_rejected_count += 1
        admin_profile.record_action()

    db.session.commit()

    current_app.logger.info(
        "ADMIN_REJECT_USER admin_id=%s target_user_id=%s reason=%s",
        current_user.id, user_id, reason,
    )
    return jsonify({
        "message": f"User '{user.username}' rejected.",
        "user_id": user_id,
    }), 200


# ── GET /admin/users ──────────────────────────────────────────────────────────

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """Return paginated list of all users with optional filters."""
    page          = request.args.get("page", 1, type=int)
    per_page      = min(request.args.get("per_page", 20, type=int), 100)
    role_filter   = request.args.get("role", "").strip()
    status_filter = request.args.get("status", "").strip()
    search        = request.args.get("search", "").strip()

    query = User.query

    if role_filter and role_filter in Role.ALL:
        query = query.filter_by(role=role_filter)

    if status_filter in ("pending", "approved", "rejected"):
        query = query.filter_by(account_status=status_filter)

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.username.ilike(like),
            )
        )

    paginated = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users = [
        {
            "id":             u.id,
            "username":       u.username,
            "email":          u.email,
            "full_name":      u.full_name,
            "role":           u.role,
            "account_status": u.account_status,
            "is_active":      u.is_active,
            "created_at":     u.created_at.isoformat(),
            "last_login":     u.last_login.isoformat() if u.last_login else None,
        }
        for u in paginated.items
    ]

    return jsonify({
        "users":  users,
        "total":  paginated.total,
        "page":   paginated.page,
        "pages":  paginated.pages,
    }), 200


# ── POST /admin/users/<user_id>/deactivate ────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_user(user_id):
    """Suspend a user — they cannot log in but their data is preserved."""
    if user_id == current_user.id:
        return jsonify({"error": "You cannot suspend your own account."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.ADMIN:
        return jsonify({"error": "Admin accounts cannot be suspended here."}), 403

    if not user.is_active:
        return jsonify({"message": "User is already suspended."}), 200

    user.is_active = False

    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    if admin_profile:
        admin_profile.users_deactivated_count += 1
        admin_profile.record_action()

    db.session.commit()

    current_app.logger.warning(
        "ADMIN_SUSPEND_USER admin_id=%s target_user_id=%s", current_user.id, user_id
    )
    return jsonify({"message": "User suspended.", "user_id": user_id}), 200


# ── POST /admin/users/<user_id>/reactivate ────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/reactivate", methods=["POST"])
@admin_required
def reactivate_user(user_id):
    """Re-enable a previously suspended user account."""
    if user_id == current_user.id:
        return jsonify({"error": "Cannot reactivate your own account this way."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.ADMIN:
        return jsonify({"error": "Use normal admin tools for admin accounts."}), 403

    user.is_active      = True
    user.account_status = "approved"   # clear any rejected/pending state too

    db.session.commit()

    current_app.logger.info(
        "ADMIN_REACTIVATE_USER admin_id=%s target_user_id=%s", current_user.id, user_id
    )
    return jsonify({"message": "User reactivated.", "user_id": user_id}), 200


# ── POST /admin/users/<user_id>/block ────────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/block", methods=["POST"])
@admin_required
def block_user(user_id):
    """
    Permanently block a user — sets account_status=rejected AND is_active=False.
    Stronger than suspend: the user sees a 'blocked' message on login attempt.
    """
    if user_id == current_user.id:
        return jsonify({"error": "You cannot block your own account."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.ADMIN:
        return jsonify({"error": "Admin accounts cannot be blocked here."}), 403

    data   = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "Blocked by administrator.")).strip()[:500]

    user.is_active        = False
    user.account_status   = "rejected"
    user.rejection_reason = reason

    db.session.commit()

    current_app.logger.warning(
        "ADMIN_BLOCK_USER admin_id=%s target_user_id=%s reason=%s",
        current_user.id, user_id, reason,
    )
    return jsonify({"message": "User blocked.", "user_id": user_id}), 200


# ── DELETE /admin/users/<user_id> ─────────────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """
    Permanently delete a user and all their data.
    Uses POST (not DELETE) so it works without CSRF exemption issues.
    Requires confirmation token in body to prevent accidental calls.
    """
    if user_id == current_user.id:
        return jsonify({"error": "You cannot delete your own account."}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == Role.ADMIN:
        return jsonify({"error": "Admin accounts cannot be deleted here."}), 403

    data    = request.get_json(silent=True) or {}
    confirm = data.get("confirm", "")
    if confirm != "DELETE":
        return jsonify({"error": "Send {\"confirm\": \"DELETE\"} to confirm deletion."}), 400

    username = user.username
    db.session.delete(user)
    db.session.commit()

    current_app.logger.warning(
        "ADMIN_DELETE_USER admin_id=%s deleted_user=%s deleted_user_id=%s",
        current_user.id, username, user_id,
    )
    return jsonify({"message": f"User '{username}' permanently deleted.", "user_id": user_id}), 200


# ── Legacy alumni-specific endpoints (backwards compatibility) ─────────────────

@admin_bp.route("/alumni/pending", methods=["GET"])
@admin_required
def list_pending_alumni():
    """List alumni specifically pending verification."""
    paginated = (
        Alumni.query
        .join(User, Alumni.user_id == User.id)
        .filter(User.account_status == "pending")
        .paginate(page=request.args.get("page", 1, type=int), per_page=20, error_out=False)
    )
    return jsonify({
        "alumni": [a.to_admin_dict() for a in paginated.items],
        "total":  paginated.total,
        "page":   paginated.page,
        "pages":  paginated.pages,
    }), 200
