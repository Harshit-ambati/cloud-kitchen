"""
Role Guard Utilities
----------------------
Helpers to classify roles and enforce basic role-level permissions.
"""

from fastapi import HTTPException
from app.roles.enums import Role
import logging

logger = logging.getLogger(__name__)


def resolve_role(role_str: str) -> Role:
    """Safely normalize a role string."""
    try:
        return Role.normalize(role_str)
    except ValueError:
        return None


def is_delivery_role(role_str: str) -> bool:
    return resolve_role(role_str) == Role.DELIVERY_AGENT


def is_kitchen_staff(role_str: str) -> bool:
    return resolve_role(role_str) == Role.KITCHEN_STAFF


def is_customer(role_str: str) -> bool:
    return resolve_role(role_str) == Role.CUSTOMER


def is_admin(role_str: str) -> bool:
    return resolve_role(role_str) == Role.SUPER_ADMIN


def is_manager(role_str: str) -> bool:
    return resolve_role(role_str) == Role.BRANCH_MANAGER


def enforce_admin_only(current_user, action: str = "perform this action") -> None:
    """Ensure only SUPER_ADMIN can perform this action."""
    if not is_admin(current_user.role):
        raise HTTPException(
            status_code=403,
            detail=f"Only super admins can {action}",
        )


def enforce_admin_or_manager(current_user, action: str = "perform this action") -> None:
    """Ensure only SUPER_ADMIN or BRANCH_MANAGER can perform this action."""
    role = resolve_role(current_user.role)
    if role in (Role.SUPER_ADMIN, Role.BRANCH_MANAGER):
        return
    raise HTTPException(
        status_code=403,
        detail=f"Only admins and branch managers can {action}",
    )
