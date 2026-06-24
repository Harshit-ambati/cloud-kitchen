"""
Branch Routes
-----------------
CRUD endpoints for branch management.

Access control:
    - GET /branches        → All authenticated users (filtered by role)
    - GET /branches/:id    → All authenticated users (filtered by role)
    - POST /branches       → SUPER_ADMIN only
    - PUT /branches/:id    → SUPER_ADMIN only
    - DELETE /branches/:id → SUPER_ADMIN only
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import PyMongoError

from app.dependencies.auth import (
    CurrentUser,
    get_current_user,
    get_current_user_optional,
    require_admin,
    log_access,
)
from app.models.branch import BranchCreate, BranchUpdate
from app.services.branch_service import (
    get_all_branches,
    get_branch_by_id,
    create_branch,
    update_branch,
    delete_branch,
)
from app.middleware.branch_isolation import BranchIsolationFilter
from app.services.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def list_branches(
    active_only: bool = Query(True, description="Filter to active branches only"),
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """
    List all branches.
    Public endpoint, but authenticated users get role-filtered results.
    """
    try:
        branches = get_all_branches(active_only=active_only)

        if current_user:
            log_access(current_user, "branches/list", len(branches))

        return success_response(
            branches=branches,
            count=len(branches),
        )
    except PyMongoError as exc:
        logger.error("DB_ERROR | list_branches failed: %s", exc)
        return error_response("Database unavailable", branches=[], count=0)


@router.get("/{branch_id}")
def get_branch(
    branch_id: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """Get a specific branch by ID."""
    branch = get_branch_by_id(branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if current_user:
        log_access(current_user, f"branches/{branch_id}", 1)

    return branch


@router.post("/", status_code=201)
def create_new_branch(
    payload: BranchCreate,
    current_user: CurrentUser = Depends(require_admin),
):
    """Create a new branch (SUPER_ADMIN only)."""
    try:
        branch = create_branch(payload)
        logger.info(
            "BRANCH_CREATED | by=%s branch=%s",
            current_user.user_id,
            branch.get("id"),
        )
        return success_response(
            message="Branch created successfully",
            branch=branch,
        )
    except PyMongoError as exc:
        logger.error("DB_ERROR | create_branch failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.put("/{branch_id}")
def update_existing_branch(
    branch_id: str,
    payload: BranchUpdate,
    current_user: CurrentUser = Depends(require_admin),
):
    """Update an existing branch (SUPER_ADMIN only)."""
    try:
        existing = get_branch_by_id(branch_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Branch not found")

        updated = update_branch(branch_id, payload)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update branch")

        logger.info(
            "BRANCH_UPDATED | by=%s branch=%s",
            current_user.user_id,
            branch_id,
        )
        return success_response(
            message="Branch updated successfully",
            branch=updated,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | update_branch failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.delete("/{branch_id}")
def delete_existing_branch(
    branch_id: str,
    current_user: CurrentUser = Depends(require_admin),
):
    """Soft-delete a branch (SUPER_ADMIN only)."""
    try:
        existing = get_branch_by_id(branch_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Branch not found")

        success = delete_branch(branch_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete branch")

        logger.info(
            "BRANCH_DELETED | by=%s branch=%s",
            current_user.user_id,
            branch_id,
        )
        return success_response(message="Branch deactivated successfully")
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | delete_branch failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.get("/{branch_id}/staff")
def get_branch_staff(
    branch_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get all staff assigned to a branch.
    SUPER_ADMIN can view any branch.
    BRANCH_MANAGER can only view their own branch.
    """
    # Branch isolation check
    if not current_user.is_super_admin:
        if current_user.branch_id != branch_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: you can only view your own branch staff",
            )

    try:
        from app.services.user_service import UserService
        staff = UserService.get_branch_staff(branch_id)
        staff_responses = [UserService.to_response(s) for s in staff]
        staff_count = UserService.get_branch_staff_count(branch_id)

        log_access(current_user, f"branches/{branch_id}/staff", len(staff_responses))

        return success_response(
            staff=[s.dict() for s in staff_responses],
            count=len(staff_responses),
            role_breakdown=staff_count,
        )
    except PyMongoError as exc:
        logger.error("DB_ERROR | get_branch_staff failed: %s", exc)
        return error_response("Database unavailable", staff=[], count=0)
