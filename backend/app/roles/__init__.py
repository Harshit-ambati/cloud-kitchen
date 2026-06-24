"""
Role & Permission System
--------------------------
Centralised role definitions, permission enums, and role-permission
mapping for the Cloud Kitchen multi-branch RBAC system.

Roles:
    SUPER_ADMIN    – Platform-wide access across all branches
    BRANCH_MANAGER – Full CRUD within their assigned branch only
    KITCHEN_STAFF  – Kitchen operations (prep, status) within their branch
    DELIVERY_AGENT – Delivery-related ops on assigned orders only
    CUSTOMER       – Self-service: own orders, profile, menu browsing

Design:
    - Enum-based roles prevent typos and ensure exhaustive matching.
    - Permissions are granular actions (verbs) on resources.
    - The ROLE_PERMISSIONS mapping is the single source of truth
      for what each role is allowed to do.
    - Helper utilities let any service or middleware query the
      permission matrix without hard-coding role strings.
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
]
