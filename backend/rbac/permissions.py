"""
rbac/permissions.py
-------------------
Fine-grained permission strings and role-to-permission mappings.

Each permission string maps to a specific action in the system.
Route decorators use these to enforce access (RBAC-01, RBAC-06).

Usage:
    from rbac.permissions import Permission, role_has_permission

    if not role_has_permission(current_user.role, Permission.VIEW_ALUMNI_PROFILES):
        abort(403)
"""

from rbac.roles import Role


# ------------------------------------------------------------------ #
# Permission string constants
# ------------------------------------------------------------------ #

class Permission:
    # ---- Alumni profile access ---- #
    VIEW_ALUMNI_PROFILES       = "view_alumni_profiles"       # RBAC-02: students only see verified
    VIEW_OWN_ALUMNI_PROFILE    = "view_own_alumni_profile"
    EDIT_OWN_ALUMNI_PROFILE    = "edit_own_alumni_profile"

    # ---- Student profile access ---- #
    VIEW_STUDENT_PROFILES      = "view_student_profiles"      # Verified alumni only
    VIEW_OWN_STUDENT_PROFILE   = "view_own_student_profile"
    EDIT_OWN_STUDENT_PROFILE   = "edit_own_student_profile"

    # ---- Mentorship ---- #
    SEND_MENTORSHIP_REQUEST    = "send_mentorship_request"    # Students only
    RESPOND_MENTORSHIP_REQUEST = "respond_mentorship_request" # Verified alumni only (RBAC-04)
    WITHDRAW_MENTORSHIP_REQUEST = "withdraw_mentorship_request"
    VIEW_OWN_MENTORSHIP        = "view_own_mentorship"

    # ---- Verification documents ---- #
    UPLOAD_VERIFICATION_DOCS   = "upload_verification_docs"   # Unverified alumni
    VIEW_OWN_DOCUMENTS         = "view_own_documents"

    # ---- Admin actions ---- #
    REVIEW_ALUMNI_VERIFICATION = "review_alumni_verification" # RBAC-05
    MANAGE_USERS               = "manage_users"               # RBAC-05
    VIEW_AUDIT_LOGS            = "view_audit_logs"            # RBAC-05
    DEACTIVATE_USER            = "deactivate_user"            # RBAC-05
    VIEW_ALL_DOCUMENTS         = "view_all_documents"         # RBAC-05


# ------------------------------------------------------------------ #
# Role → Permission mapping  (RBAC-01 through RBAC-06)
# ------------------------------------------------------------------ #

_ROLE_PERMISSIONS: dict[str, set] = {

    Role.STUDENT: {
        Permission.VIEW_ALUMNI_PROFILES,
        Permission.VIEW_OWN_STUDENT_PROFILE,
        Permission.EDIT_OWN_STUDENT_PROFILE,
        Permission.SEND_MENTORSHIP_REQUEST,
        Permission.WITHDRAW_MENTORSHIP_REQUEST,
        Permission.VIEW_OWN_MENTORSHIP,
    },

    # Unverified alumni: very limited — cannot interact with students (RBAC-03)
    Role.UNVERIFIED_ALUMNI: {
        Permission.VIEW_OWN_ALUMNI_PROFILE,
        Permission.EDIT_OWN_ALUMNI_PROFILE,
        Permission.UPLOAD_VERIFICATION_DOCS,
        Permission.VIEW_OWN_DOCUMENTS,
    },

    # Verified alumni: full mentorship participation (RBAC-04)
    Role.VERIFIED_ALUMNI: {
        Permission.VIEW_OWN_ALUMNI_PROFILE,
        Permission.EDIT_OWN_ALUMNI_PROFILE,
        Permission.VIEW_STUDENT_PROFILES,
        Permission.RESPOND_MENTORSHIP_REQUEST,
        Permission.VIEW_OWN_MENTORSHIP,
        Permission.VIEW_OWN_DOCUMENTS,
    },

    # Admin: all permissions (RBAC-05)
    Role.ADMIN: {
        Permission.VIEW_ALUMNI_PROFILES,
        Permission.VIEW_STUDENT_PROFILES,
        Permission.REVIEW_ALUMNI_VERIFICATION,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.DEACTIVATE_USER,
        Permission.VIEW_ALL_DOCUMENTS,
        Permission.VIEW_OWN_MENTORSHIP,
    },
}


def role_has_permission(role: str, permission: str) -> bool:
    """
    Return True if the given role includes the requested permission.
    All checks happen server-side — clients cannot influence this (RBAC-06).
    """
    return permission in _ROLE_PERMISSIONS.get(role, set())


def get_permissions_for_role(role: str) -> set:
    """Return the full set of permissions for a role (read-only copy)."""
    return frozenset(_ROLE_PERMISSIONS.get(role, set()))
