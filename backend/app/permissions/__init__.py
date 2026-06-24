"""
Permissions Package
---------------------
Re-exports permission utilities for convenience.

Usage:
    from app.permissions import has_permission, Permission, Role
"""

from app.roles.enums import Role, Permission
from app.roles.permissions import (
    ROLE_PERMISSIONS,
    has_permission,
    has_any_permission,
    has_all_permissions,
    get_permissions,
    is_internal_role,
    requires_branch,
    can_manage_users,
    get_manageable_roles,
    INTERNAL_ROLES,
    CUSTOMER_ROLES,
    BRANCH_REQUIRED_ROLES,
    USER_MANAGEMENT_ROLES,
)

from app.permissions.role_guards import (
    resolve_role,
    is_delivery_role,
    is_kitchen_staff,
    is_customer,
    is_admin,
    is_manager,
    enforce_admin_only,
    enforce_admin_or_manager,
)
from app.permissions.ownership import enforce_ownership
from app.permissions.branch_scope import enforce_branch_match
from app.permissions.delivery_scope import (
    enforce_not_delivery,
    filter_agent_update,
    enforce_delivery_status_permission,
)
from app.permissions.kitchen_scope import (
    enforce_kitchen_or_above,
    enforce_kitchen_status_permission,
)

__all__ = [
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "has_permission",
    "has_any_permission",
    "has_all_permissions",
    "get_permissions",
    "is_internal_role",
    "requires_branch",
    "can_manage_users",
    "get_manageable_roles",
    "INTERNAL_ROLES",
    "CUSTOMER_ROLES",
    "BRANCH_REQUIRED_ROLES",
    "USER_MANAGEMENT_ROLES",
    "resolve_role",
    "is_delivery_role",
    "is_kitchen_staff",
    "is_customer",
    "is_admin",
    "is_manager",
    "enforce_admin_only",
    "enforce_admin_or_manager",
    "enforce_ownership",
    "enforce_branch_match",
    "enforce_not_delivery",
    "filter_agent_update",
    "enforce_delivery_status_permission",
    "enforce_kitchen_or_above",
    "enforce_kitchen_status_permission",
]
