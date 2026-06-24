"""
Role & Permission Enums
-------------------------
String-backed enums that are JSON-serialisable and MongoDB-friendly.
Using StrEnum ensures that role values stored in the database are plain
strings, while Python code benefits from IDE autocomplete and
exhaustiveness checks.

Design decisions:
    - Legacy role values (admin, manager, delivery, agent) are NOT
      enum members. They are handled via a static mapping in
      normalize(), keeping the enum clean for new code.
    - Permission strings follow RESOURCE:ACTION format for easy
      parsing in audit logs and policy engines.
"""

from enum import Enum
from typing import Dict


# ── Legacy role string → canonical role value mapping ─────────────────
# Kept outside the enum so the enum only contains canonical members.
_LEGACY_ROLE_MAP: Dict[str, str] = {
    "admin": "super_admin",
    "manager": "branch_manager",
    "delivery": "delivery_agent",
    "agent": "delivery_agent",
}


class Role(str, Enum):
    """
    Platform roles — canonical values only.
    The string value is what gets stored in MongoDB and JWT payloads.
    """
    SUPER_ADMIN = "super_admin"
    BRANCH_MANAGER = "branch_manager"
    KITCHEN_STAFF = "kitchen_staff"
    DELIVERY_AGENT = "delivery_agent"
    CUSTOMER = "customer"

    @classmethod
    def normalize(cls, raw: str) -> "Role":
        """
        Convert any raw role string (including legacy values) to the
        canonical Role enum member.

        Raises ValueError for truly unknown roles.
        """
        # Try direct match first
        try:
            return cls(raw)
        except ValueError:
            pass
        # Try legacy mapping (case-insensitive)
        mapped_value = _LEGACY_ROLE_MAP.get(raw.lower())
        if mapped_value:
            return cls(mapped_value)
        raise ValueError(f"Unknown role: {raw!r}")

    @classmethod
    def all_canonical(cls) -> list["Role"]:
        """Return all canonical (non-legacy) roles."""
        return [cls.SUPER_ADMIN, cls.BRANCH_MANAGER, cls.KITCHEN_STAFF, cls.DELIVERY_AGENT, cls.CUSTOMER]

    @property
    def display_name(self) -> str:
        """Human-readable label for dashboards and logs."""
        return _ROLE_DISPLAY_NAMES.get(self.value, self.value.replace("_", " ").title())

    @property
    def hierarchy_level(self) -> int:
        """
        Numeric hierarchy level for comparison.
        Higher number = more privilege.
        Useful for "at least this level" checks.
        """
        return _ROLE_HIERARCHY.get(self, 0)

    def __ge__(self, other: "Role") -> bool:
        if not isinstance(other, Role):
            return NotImplemented
        return self.hierarchy_level >= other.hierarchy_level

    def __gt__(self, other: "Role") -> bool:
        if not isinstance(other, Role):
            return NotImplemented
        return self.hierarchy_level > other.hierarchy_level

    def __le__(self, other: "Role") -> bool:
        if not isinstance(other, Role):
            return NotImplemented
        return self.hierarchy_level <= other.hierarchy_level

    def __lt__(self, other: "Role") -> bool:
        if not isinstance(other, Role):
            return NotImplemented
        return self.hierarchy_level < other.hierarchy_level


# ── Display names ─────────────────────────────────────────────────────
_ROLE_DISPLAY_NAMES: Dict[str, str] = {
    "super_admin": "Super Admin",
    "branch_manager": "Branch Manager",
    "kitchen_staff": "Kitchen Staff",
    "delivery_agent": "Delivery Agent",
    "customer": "Customer",
}

# ── Role hierarchy (higher = more privilege) ──────────────────────────
_ROLE_HIERARCHY: Dict[Role, int] = {
    Role.CUSTOMER: 10,
    Role.DELIVERY_AGENT: 20,
    Role.KITCHEN_STAFF: 30,
    Role.BRANCH_MANAGER: 40,
    Role.SUPER_ADMIN: 100,
}


class Permission(str, Enum):
    """
    Granular action permissions.
    Format: RESOURCE:ACTION (e.g. orders:create, agents:delete).
    """

    # ── Orders ────────────────────────────────────────────────────────
    ORDERS_CREATE = "orders:create"
    ORDERS_READ = "orders:read"
    ORDERS_READ_OWN = "orders:read_own"
    ORDERS_UPDATE_STATUS = "orders:update_status"
    ORDERS_UPDATE_DELIVERY_STATUS = "orders:update_delivery_status"
    ORDERS_DELETE = "orders:delete"
    ORDERS_ASSIGN = "orders:assign"

    # ── Agents / Delivery ─────────────────────────────────────────────
    AGENTS_CREATE = "agents:create"
    AGENTS_READ = "agents:read"
    AGENTS_READ_OWN = "agents:read_own"
    AGENTS_UPDATE = "agents:update"
    AGENTS_UPDATE_OWN = "agents:update_own"
    AGENTS_DELETE = "agents:delete"

    # ── Menu ──────────────────────────────────────────────────────────
    MENU_READ = "menu:read"
    MENU_CREATE = "menu:create"
    MENU_UPDATE = "menu:update"
    MENU_DELETE = "menu:delete"

    # ── Branches ──────────────────────────────────────────────────────
    BRANCHES_CREATE = "branches:create"
    BRANCHES_READ = "branches:read"
    BRANCHES_READ_OWN = "branches:read_own"
    BRANCHES_UPDATE = "branches:update"
    BRANCHES_DELETE = "branches:delete"

    # ── Users ─────────────────────────────────────────────────────────
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_READ_OWN = "users:read_own"
    USERS_UPDATE = "users:update"
    USERS_UPDATE_OWN = "users:update_own"
    USERS_DELETE = "users:delete"

    # ── Analytics / Metrics ───────────────────────────────────────────
    METRICS_READ = "metrics:read"
    METRICS_READ_BRANCH = "metrics:read_branch"

    # ── Kitchen operations ────────────────────────────────────────────
    KITCHEN_READ_QUEUE = "kitchen:read_queue"
    KITCHEN_UPDATE_PREP = "kitchen:update_prep"

    # ── System / Internal ─────────────────────────────────────────────
    SYSTEM_HEALTH = "system:health"
    SYSTEM_INTERNAL = "system:internal"

    @property
    def resource(self) -> str:
        """Extract the resource part (e.g. 'orders' from 'orders:create')."""
        return self.value.split(":")[0]

    @property
    def action(self) -> str:
        """Extract the action part (e.g. 'create' from 'orders:create')."""
        return self.value.split(":")[1]
