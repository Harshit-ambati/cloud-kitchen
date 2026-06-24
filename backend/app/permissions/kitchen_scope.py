"""
Kitchen Scope Validation
--------------------------
Enforces rules specifically for kitchen staff operations.
"""

from fastapi import HTTPException
from app.permissions.role_guards import resolve_role, is_kitchen_staff
from app.roles.enums import Role

# Kitchen staff can set these statuses
KITCHEN_ALLOWED_STATUSES = {"accepted", "ready_for_pickup", "in_transit"}


def enforce_kitchen_or_above(current_user, action: str = "perform this action") -> None:
    """Ensure KITCHEN_STAFF, BRANCH_MANAGER, or SUPER_ADMIN can perform this action."""
    role = resolve_role(current_user.role)
    if role in (Role.SUPER_ADMIN, Role.BRANCH_MANAGER, Role.KITCHEN_STAFF):
        return
    raise HTTPException(
        status_code=403,
        detail=f"Only kitchen staff and above can {action}",
    )


def enforce_kitchen_status_permission(current_user, new_status: str) -> None:
    """Ensure kitchen staff only use allowed statuses."""
    if is_kitchen_staff(current_user.role):
        if new_status not in KITCHEN_ALLOWED_STATUSES:
            raise HTTPException(
                status_code=403,
                detail=f"Kitchen staff can only set status to: {', '.join(sorted(KITCHEN_ALLOWED_STATUSES))}",
            )
