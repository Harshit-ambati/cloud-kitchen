"""
User Management Routes
------------------------
Admin endpoints for managing platform users.

Access control:
    - GET /users          → SUPER_ADMIN, BRANCH_MANAGER (branch-scoped)
    - GET /users/:id      → SUPER_ADMIN, BRANCH_MANAGER (branch-scoped), self
    - POST /users         → SUPER_ADMIN, BRANCH_MANAGER
    - PUT /users/:id      → SUPER_ADMIN, BRANCH_MANAGER (branch-scoped), self (limited)
    - DELETE /users/:id   → SUPER_ADMIN only
"""

import logging
from datetime import datetime
from typing import Optional

from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import PyMongoError

from app.dependencies.auth import (
    CurrentUser,
    get_current_user,
    build_user_filter,
    log_access,
)
from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.roles.enums import Role
from app.roles.permissions import requires_branch, can_manage_users
from app.services.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()

user_service = UserService()


@router.get("/")
def list_users(
    current_user: CurrentUser = Depends(get_current_user),
    role: Optional[str] = Query(None, description="Filter by role"),
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    active_only: bool = Query(True, description="Show only active users"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List users with role-based filtering.
    SUPER_ADMIN sees all users.
    BRANCH_MANAGER sees only their branch staff.
    """
    if not can_manage_users(current_user.role):
        raise HTTPException(status_code=403, detail="Insufficient permissions to list users")

    try:
        # Build base query with role-based scoping
        query = build_user_filter(current_user)

        # Apply optional filters
        if role:
            try:
                role_enum = Role.normalize(role)
                query["role"] = role_enum.value
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid role filter: {role}")

        if branch_id:
            # Branch managers can't filter other branches
            if not current_user.is_super_admin and current_user.branch_id != branch_id:
                raise HTTPException(status_code=403, detail="Cannot view users from other branches")
            query["branch_id"] = branch_id

        if active_only:
            query["is_active"] = True

        users = user_service.list_users(query, skip=skip, limit=limit)
        total = user_service.count_users(query)

        user_responses = [user_service.to_response(u).dict() for u in users]
        log_access(current_user, "users/list", len(user_responses))

        return success_response(
            users=user_responses,
            count=len(user_responses),
            total=total,
            skip=skip,
            limit=limit,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | list_users failed: %s", exc)
        return error_response("Database unavailable", users=[], count=0)


@router.get("/{user_id}")
def get_user(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get a specific user by ID.
    Users can always view their own profile.
    Managers can view users in their branch.
    Admins can view anyone.
    """
    try:
        # Self-access is always allowed
        is_self = current_user.user_id == user_id

        if not is_self and not can_manage_users(current_user.role):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Branch isolation for managers
        if not current_user.is_super_admin and not is_self:
            if user.get("branch_id") != current_user.branch_id:
                raise HTTPException(status_code=403, detail="Access denied: user is not in your branch")

        log_access(current_user, f"users/{user_id}", 1)
        return user_service.to_response(user).dict()
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | get_user failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.post("/", status_code=201)
def create_user(
    payload: UserCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Create a new user (admin/manager only).
    Enforces privilege escalation prevention.
    """
    if not can_manage_users(current_user.role):
        raise HTTPException(status_code=403, detail="Insufficient permissions to create users")

    try:
        # Privilege escalation check
        user_service.validate_role_assignment(current_user.role, payload.role)

        # Branch managers must assign to their own branch
        branch_id = payload.branch_id
        if current_user.is_branch_manager:
            if requires_branch(payload.role) and branch_id != current_user.branch_id:
                branch_id = current_user.branch_id  # Force to own branch

        user = user_service.create_user(
            email=payload.email,
            password=payload.password,
            role=payload.role,
            branch_id=branch_id,
            name=payload.name,
            phone=payload.phone,
            address=payload.address,
            created_by=current_user.user_id,
        )

        role_enum = Role.normalize(payload.role)
        logger.info(
            "USER_CREATED | by=%s new_user=%s role=%s branch=%s",
            current_user.user_id,
            str(user["_id"]),
            payload.role,
            branch_id,
        )

        return success_response(
            message="User created successfully",
            user_id=str(user["_id"]),
            role=role_enum.value,
            role_display=role_enum.display_name,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | create_user failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.put("/{user_id}")
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Update a user.
    Self-update is limited to name, email, phone, address.
    Managers can update branch staff (not roles above their own).
    Admins can update anyone.
    """
    try:
        is_self = current_user.user_id == user_id

        if not is_self and not can_manage_users(current_user.role):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Self-update restrictions
        if is_self and not current_user.is_super_admin:
            allowed_self_fields = {"name", "email", "phone", "address"}
            restricted = set(update_data.keys()) - allowed_self_fields
            if restricted:
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot self-update fields: {', '.join(restricted)}",
                )

        # Role change validation
        if "role" in update_data:
            user_service.validate_role_assignment(current_user.role, update_data["role"])

        # Branch isolation for managers
        if not current_user.is_super_admin and not is_self:
            existing = user_service.get_user_by_id(user_id)
            if not existing:
                raise HTTPException(status_code=404, detail="User not found")
            if existing.get("branch_id") != current_user.branch_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: user is not in your branch",
                )

        updated = user_service.update_user(user_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(
            "USER_UPDATED | by=%s target=%s fields=%s",
            current_user.user_id,
            user_id,
            list(update_data.keys()),
        )

        return success_response(
            message="User updated successfully",
            user=user_service.to_response(updated).dict(),
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | update_user failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Soft-delete a user (deactivate).
    SUPER_ADMIN only. Cannot deactivate yourself.
    """
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can deactivate users")

    if current_user.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    try:
        existing = user_service.get_user_by_id(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")

        success = user_service.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to deactivate user")

        logger.info(
            "USER_DEACTIVATED | by=%s target=%s",
            current_user.user_id,
            user_id,
        )

        return success_response(message="User deactivated successfully")
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | delete_user failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
