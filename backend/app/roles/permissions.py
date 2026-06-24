"""
Role → Permission Mapping
----------------------------
Single source of truth for what each role can do.
Used by middleware, route guards, and policy enforcement.

Design:
    - ROLE_PERMISSIONS maps canonical Role → frozenset of Permissions.
    - Helper utilities accept both Role enums and raw strings.
    - Legacy role strings are normalized transparently.
"""

from typing import FrozenSet

from app.roles.enums import Permission, Role

# ── Role groupings ────────────────────────────────────────────────────

INTERNAL_ROLES: FrozenSet[Role] = frozenset({
    Role.SUPER_ADMIN,
    Role.BRANCH_MANAGER,
    Role.KITCHEN_STAFF,
    Role.DELIVERY_AGENT,
})

CUSTOMER_ROLES: FrozenSet[Role] = frozenset({
    Role.CUSTOMER,
})

# Roles that MUST have a branch_id assigned
BRANCH_REQUIRED_ROLES: FrozenSet[Role] = frozenset({
    Role.BRANCH_MANAGER,
    Role.KITCHEN_STAFF,
    Role.DELIVERY_AGENT,
})

# Roles that can manage other users
USER_MANAGEMENT_ROLES: FrozenSet[Role] = frozenset({
    Role.SUPER_ADMIN,
    Role.BRANCH_MANAGER,
})

# ── Permission matrix ─────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[Role, FrozenSet[Permission]] = {

    Role.SUPER_ADMIN: frozenset(Permission),  # all permissions

    Role.BRANCH_MANAGER: frozenset({
        # Orders — full CRUD within branch
        Permission.ORDERS_CREATE,
        Permission.ORDERS_READ,
        Permission.ORDERS_UPDATE_STATUS,
        Permission.ORDERS_ASSIGN,
        # Agents — manage branch agents
        Permission.AGENTS_CREATE,
        Permission.AGENTS_READ,
        Permission.AGENTS_UPDATE,
        Permission.AGENTS_DELETE,
        # Menu — manage branch menu
        Permission.MENU_READ,
        Permission.MENU_CREATE,
        Permission.MENU_UPDATE,
        Permission.MENU_DELETE,
        # Branch — read own
        Permission.BRANCHES_READ_OWN,
        # Users — read own branch staff
        Permission.USERS_READ,
        Permission.USERS_CREATE,
        Permission.USERS_READ_OWN,
        # Kitchen
        Permission.KITCHEN_READ_QUEUE,
        Permission.KITCHEN_UPDATE_PREP,
        # Metrics — branch-level
        Permission.METRICS_READ_BRANCH,
        # System
        Permission.SYSTEM_HEALTH,
    }),

    Role.KITCHEN_STAFF: frozenset({
        # Orders — read branch orders, update prep status
        Permission.ORDERS_READ,
        Permission.ORDERS_UPDATE_STATUS,
        # Menu — read only
        Permission.MENU_READ,
        # Kitchen operations
        Permission.KITCHEN_READ_QUEUE,
        Permission.KITCHEN_UPDATE_PREP,
        # Branch — read own
        Permission.BRANCHES_READ_OWN,
        # Profile
        Permission.USERS_READ_OWN,
        Permission.USERS_UPDATE_OWN,
        # System
        Permission.SYSTEM_HEALTH,
    }),

    Role.DELIVERY_AGENT: frozenset({
        # Orders — read assigned, update delivery status
        Permission.ORDERS_READ_OWN,
        Permission.ORDERS_UPDATE_DELIVERY_STATUS,
        # Agents — read/update own profile
        Permission.AGENTS_READ_OWN,
        Permission.AGENTS_UPDATE_OWN,
        # Menu — browse
        Permission.MENU_READ,
        # Branch — read own
        Permission.BRANCHES_READ_OWN,
        # Profile
        Permission.USERS_READ_OWN,
        Permission.USERS_UPDATE_OWN,
        # System
        Permission.SYSTEM_HEALTH,
    }),

    Role.CUSTOMER: frozenset({
        # Orders — create and read own
        Permission.ORDERS_CREATE,
        Permission.ORDERS_READ_OWN,
        # Menu — browse
        Permission.MENU_READ,
        # Branches — browse
        Permission.BRANCHES_READ,
        # Profile
        Permission.USERS_READ_OWN,
        Permission.USERS_UPDATE_OWN,
    }),
}


# ── Helper utilities ──────────────────────────────────────────────────

def _resolve_role(role: Role | str) -> Role:
    """Convert a raw string to a canonical Role, or return as-is."""
    if isinstance(role, str):
        return Role.normalize(role)
    return role


def has_permission(role: Role | str, permission: Permission) -> bool:
    """
    Check if a role has a specific permission.
    Accepts raw string role values for convenience.
    """
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(resolved, frozenset())


def has_any_permission(role: Role | str, *permissions: Permission) -> bool:
    """Check if a role has ANY of the given permissions."""
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return False
    role_perms = ROLE_PERMISSIONS.get(resolved, frozenset())
    return any(p in role_perms for p in permissions)


def has_all_permissions(role: Role | str, *permissions: Permission) -> bool:
    """Check if a role has ALL of the given permissions."""
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return False
    role_perms = ROLE_PERMISSIONS.get(resolved, frozenset())
    return all(p in role_perms for p in permissions)


def get_permissions(role: Role | str) -> FrozenSet[Permission]:
    """Return the full permission set for a role."""
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return frozenset()
    return ROLE_PERMISSIONS.get(resolved, frozenset())


def is_internal_role(role: Role | str) -> bool:
    """Check if a role is an internal (staff) role vs customer."""
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return False
    return resolved in INTERNAL_ROLES


def requires_branch(role: Role | str) -> bool:
    """Check if a role must have a branch_id assigned."""
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return False
    return resolved in BRANCH_REQUIRED_ROLES


def can_manage_users(role: Role | str) -> bool:
    """Check if a role can create/update/delete other users."""
    try:
        resolved = _resolve_role(role)
    except ValueError:
        return False
    return resolved in USER_MANAGEMENT_ROLES


def get_manageable_roles(manager_role: Role | str) -> list[Role]:
    """
    Return the list of roles that a manager can assign to users.
    Prevents privilege escalation (can't create users with higher roles).
    """
    try:
        resolved = _resolve_role(manager_role)
    except ValueError:
        return []

    if resolved == Role.SUPER_ADMIN:
        # Super admin can create any role
        return Role.all_canonical()

    if resolved == Role.BRANCH_MANAGER:
        # Branch managers can create kitchen staff, delivery agents, and customers
        return [Role.KITCHEN_STAFF, Role.DELIVERY_AGENT, Role.CUSTOMER]

    return []
