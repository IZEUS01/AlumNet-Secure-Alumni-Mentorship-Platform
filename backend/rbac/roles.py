"""
rbac/roles.py
-------------
Single source of truth for all role definitions, hierarchy, and
role-to-permission mappings.

Mirrors the DB enum in models/user.py — keep both in sync if roles change.

Security controls:
    RBAC-01  — All resources guarded by role checks
    RBAC-02  — Students: browse verified alumni only
    RBAC-03  — Unverified alumni cannot interact with students
    RBAC-04  — Verified alumni can respond to mentorship requests
    RBAC-05  — Admin-only functions isolated
    RBAC-06  — Role constants defined here; validated server-side only
"""

from __future__ import annotations


# ------------------------------------------------------------------ #
# Role string constants
# ------------------------------------------------------------------ #

class Role:
    STUDENT           = "student"
    UNVERIFIED_ALUMNI = "unverified_alumni"
    VERIFIED_ALUMNI   = "verified_alumni"
    ADMIN             = "admin"

    # Convenience sets
    ALL: frozenset = frozenset({
        STUDENT, UNVERIFIED_ALUMNI, VERIFIED_ALUMNI, ADMIN
    })

    ALUMNI_ANY: frozenset = frozenset({
        UNVERIFIED_ALUMNI, VERIFIED_ALUMNI
    })

    # Roles that can access mentorship features (RBAC-03, RBAC-04)
    MENTORSHIP_CAPABLE: frozenset = frozenset({
        STUDENT, VERIFIED_ALUMNI
    })


# ------------------------------------------------------------------ #
# Role hierarchy
# Higher numeric value = more privileged.
# ------------------------------------------------------------------ #

ROLE_HIERARCHY = {
    Role.STUDENT:           1,
    Role.UNVERIFIED_ALUMNI: 2,
    Role.VERIFIED_ALUMNI:   3,
    Role.ADMIN:             4,
}


def has_minimum_role(user_role: str, minimum: str) -> bool:
    """
    Return True if user_role is at least as privileged as minimum.

    Example:
        has_minimum_role("admin", "verified_alumni")   # True
        has_minimum_role("student", "verified_alumni") # False
    """
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(minimum, 0)


# ------------------------------------------------------------------ #
# Human-readable role labels (for UI / logs)
# ------------------------------------------------------------------ #

ROLE_LABELS = {
    Role.STUDENT:           "Student",
    Role.UNVERIFIED_ALUMNI: "Unverified Alumni",
    Role.VERIFIED_ALUMNI:   "Verified Alumni",
    Role.ADMIN:             "Administrator",
}


def get_role_label(role: str) -> str:
    """Return the display label for a role string."""
    return ROLE_LABELS.get(role, "Unknown")
