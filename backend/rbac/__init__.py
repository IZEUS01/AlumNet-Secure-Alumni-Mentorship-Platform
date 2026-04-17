# rbac/__init__.py
# RBAC module — exposes roles, permissions, and helpers.

from .roles       import Role, ROLE_HIERARCHY, ROLE_LABELS, has_minimum_role, get_role_label
from .permissions import Permission, role_has_permission, get_permissions_for_role

__all__ = [
    "Role",
    "ROLE_HIERARCHY",
    "ROLE_LABELS",
    "has_minimum_role",
    "get_role_label",
    "Permission",
    "role_has_permission",
    "get_permissions_for_role",
]
