"""
Role Policy Enforcement
------------------------
Centralised RBAC policy helpers used across all routes.

Policy Matrix:
    admin    → full access, all branches
    manager  → CRUD within assigned branch_id(s)
    delivery → read assigned orders only, update own location/status
    agent    → alias for delivery
"""

import logging
from fastapi import HTTPException
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.dependencies.auth import CurrentUser

logger = logging.getLogger(__name__)


# ── Ownership enforcement ─────────────────────────────────────────────

def enforce_ownership(current_user: "CurrentUser", resource_owner_id: str) -> None:
    """
    Agents / delivery users can only operate on resources they own.
    Admins and managers are exempt (branch scoping is handled elsewhere).

    Raises HTTP 403 if the calling user is a delivery/agent and
    resource_owner_id does not match their user_id.
    """
    if current_user.role in ("delivery", "agent"):
        if current_user.user_id != resource_owner_id:
            logger.warning(
                "POLICY_BLOCK | user=%s role=%s tried to access resource owned by %s",
                current_user.user_id, current_user.role, resource_owner_id,
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: you can only access your own resources",
            )


def enforce_not_delivery(current_user: "CurrentUser", action: str = "perform this action") -> None:
    """Block delivery/agent users from write operations they shouldn't have."""
    if current_user.role in ("delivery", "agent"):
        raise HTTPException(
            status_code=403,
            detail=f"Delivery/Agent users cannot {action}",
        )


# ── Agent update scope ────────────────────────────────────────────────

# Fields that delivery/agent users are allowed to update on their own
# agent profile.  Any fields NOT in this set are silently stripped.
AGENT_SELF_UPDATE_FIELDS = {"lat", "lng", "available"}


def filter_agent_update(current_user: "CurrentUser", update_data: dict) -> dict:
    """
    If the caller is a delivery/agent, restrict the update payload
    to only the fields they are allowed to change (location + availability).
    Admins and managers may update any field.
    """
    if current_user.role in ("delivery", "agent"):
        filtered = {k: v for k, v in update_data.items() if k in AGENT_SELF_UPDATE_FIELDS}
        stripped = set(update_data) - AGENT_SELF_UPDATE_FIELDS
        if stripped:
            logger.info(
                "POLICY_FILTER | agent %s tried to update restricted fields: %s (stripped)",
                current_user.user_id, stripped,
            )
        return filtered
    return update_data


# ── Status update scope for delivery ──────────────────────────────────

# Delivery users can only set these statuses on orders assigned to them.
DELIVERY_ALLOWED_STATUSES = {"in_transit", "delivered"}


def enforce_delivery_status_permission(
    current_user: "CurrentUser", new_status: str
) -> None:
    """
    Delivery/agent users may only transition orders to delivery-related
    statuses.  Kitchen-side transitions (accepted, ready_for_pickup, etc.)
    are reserved for admin/manager.
    """
    if current_user.role in ("delivery", "agent"):
        if new_status not in DELIVERY_ALLOWED_STATUSES:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Delivery users can only set status to: "
                    f"{', '.join(sorted(DELIVERY_ALLOWED_STATUSES))}"
                ),
            )
