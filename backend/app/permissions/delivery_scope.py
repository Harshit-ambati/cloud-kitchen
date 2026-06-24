"""
Delivery Scope Validation
---------------------------
Enforces rules specifically for delivery agents and their assignments.
"""

import logging
from fastapi import HTTPException
from app.permissions.role_guards import is_delivery_role, is_customer, is_kitchen_staff

logger = logging.getLogger(__name__)

# Delivery users can only set these statuses on orders assigned to them.
DELIVERY_ALLOWED_STATUSES = {"in_transit", "delivered"}

# Fields that delivery/agent users are allowed to update on their own agent profile.
AGENT_SELF_UPDATE_FIELDS = {"lat", "lng", "available"}


def enforce_not_delivery(current_user, action: str = "perform this action") -> None:
    """Block delivery/agent and customer users from write operations they shouldn't have."""
    if is_delivery_role(current_user.role):
        raise HTTPException(
            status_code=403,
            detail=f"Delivery/Agent users cannot {action}",
        )
    if is_customer(current_user.role):
        raise HTTPException(
            status_code=403,
            detail=f"Customer users cannot {action}",
        )


def filter_agent_update(current_user, update_data: dict) -> dict:
    """
    If the caller is a delivery/agent, restrict the update payload
    to only the fields they are allowed to change.
    """
    if is_delivery_role(current_user.role):
        filtered = {k: v for k, v in update_data.items() if k in AGENT_SELF_UPDATE_FIELDS}
        stripped = set(update_data) - AGENT_SELF_UPDATE_FIELDS
        if stripped:
            logger.info(
                "POLICY_FILTER | agent %s tried to update restricted fields: %s (stripped)",
                current_user.user_id, stripped,
            )
        return filtered
    return update_data


def enforce_delivery_status_permission(current_user, new_status: str) -> None:
    """Delivery users may only transition orders to delivery-related statuses."""
    if is_delivery_role(current_user.role):
        if new_status not in DELIVERY_ALLOWED_STATUSES:
            raise HTTPException(
                status_code=403,
                detail=f"Delivery users can only set status to: {', '.join(sorted(DELIVERY_ALLOWED_STATUSES))}",
            )

    if is_customer(current_user.role):
        raise HTTPException(
            status_code=403,
            detail="Customers cannot update order status",
        )
