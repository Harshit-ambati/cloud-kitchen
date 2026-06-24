"""
Ownership Validation
----------------------
Enforces that users can only access or modify their own data.
"""

import logging
from fastapi import HTTPException
from app.permissions.role_guards import is_delivery_role, is_customer

logger = logging.getLogger(__name__)


def enforce_ownership(current_user, resource_owner_id: str) -> None:
    """
    Agents / delivery / customer users can only operate on resources they own.
    Admins and managers are exempt (branch scoping is handled elsewhere).

    Raises HTTP 403 if the calling user is a delivery/agent/customer and
    resource_owner_id does not match their user_id.
    """
    if is_delivery_role(current_user.role) or is_customer(current_user.role):
        if current_user.user_id != resource_owner_id:
            logger.warning(
                "POLICY_BLOCK | user=%s role=%s tried to access resource owned by %s",
                current_user.user_id, current_user.role, resource_owner_id,
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: you can only access your own resources",
            )
