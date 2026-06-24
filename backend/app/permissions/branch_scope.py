"""
Branch Scope Validation
-------------------------
Enforces branch isolation to prevent cross-branch access.
"""

import logging
from fastapi import HTTPException
from app.permissions.role_guards import is_admin

logger = logging.getLogger(__name__)


def enforce_branch_match(current_user, target_branch_id: str) -> None:
    """
    Ensure the user has access to the target branch.
    SUPER_ADMIN bypasses this check.
    """
    if is_admin(current_user.role):
        return

    if current_user.branch_id != target_branch_id:
        logger.warning(
            "BRANCH_MISMATCH | user=%s branch=%s tried to access branch=%s",
            current_user.user_id, current_user.branch_id, target_branch_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: you can only access your assigned branch",
        )
