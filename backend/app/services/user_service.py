"""
User Service
--------------
Business logic for user CRUD operations.
Enforces RBAC rules, branch isolation, and privilege escalation prevention.

Usage:
    from app.services.user_service import UserService

    service = UserService()
    user = service.get_user_by_id("abc123")
    users = service.list_users_for_manager(current_user)
"""

import logging
from datetime import datetime
from typing import List, Optional

from bson.objectid import ObjectId
from fastapi import HTTPException
from pymongo.errors import PyMongoError

from app.db import db
from app.auth.password import hash_password
from app.roles.enums import Role
from app.roles.permissions import (
    requires_branch,
    can_manage_users,
    get_manageable_roles,
)
from app.models.user import UserResponse

logger = logging.getLogger(__name__)

users_collection = db["users"]


class UserService:
    """Encapsulates all user-related business logic."""

    # ── Read operations ───────────────────────────────────────────────

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[dict]:
        """Fetch a user document by MongoDB _id or user_id field."""
        try:
            oid = ObjectId(user_id)
            user = users_collection.find_one({"_id": oid})
            if user:
                return user
        except Exception:
            pass
        return users_collection.find_one({"user_id": user_id})

    @staticmethod
    def get_user_by_email(email: str) -> Optional[dict]:
        """Fetch a user document by email."""
        return users_collection.find_one({"email": email})

    @staticmethod
    def list_users(
        query: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        sort_field: str = "created_at",
        sort_order: int = -1,
    ) -> List[dict]:
        """List users matching a query with pagination."""
        try:
            cursor = (
                users_collection
                .find(query or {})
                .sort(sort_field, sort_order)
                .skip(skip)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError as exc:
            logger.error("USER_SERVICE | list_users failed: %s", exc)
            return []

    @staticmethod
    def count_users(query: Optional[dict] = None) -> int:
        """Count users matching a query."""
        try:
            return users_collection.count_documents(query or {})
        except PyMongoError:
            return 0

    # ── Write operations ──────────────────────────────────────────────

    @staticmethod
    def create_user(
        email: str,
        password: str,
        role: str,
        branch_id: Optional[str] = None,
        name: str = "",
        phone: str = "",
        address: str = "",
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Create a new user with full validation.

        Validates:
            - Role is valid
            - Internal staff roles have branch_id
            - Email is unique
        """
        # Validate role
        try:
            role_enum = Role.normalize(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

        # Validate branch requirement
        if requires_branch(role_enum) and not branch_id:
            raise HTTPException(
                status_code=400,
                detail=f"Role '{role_enum.display_name}' requires a branch_id",
            )

        # Check duplicate email
        if users_collection.find_one({"email": email}):
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists",
            )

        now = datetime.utcnow()
        doc = {
            "email": email,
            "password": hash_password(password),
            "role": role_enum.value,  # Always store canonical value
            "branch_id": branch_id,
            "name": name,
            "phone": phone,
            "address": address,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
        }

        result = users_collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def update_user(user_id: str, update_data: dict) -> Optional[dict]:
        """
        Update a user document.
        Returns the updated document or None if not found.
        """
        # Validate role if being changed
        if "role" in update_data:
            try:
                role_enum = Role.normalize(update_data["role"])
                update_data["role"] = role_enum.value
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid role: {update_data['role']}",
                )

        update_data["updated_at"] = datetime.utcnow()

        try:
            oid = ObjectId(user_id)
        except Exception:
            return None

        result = users_collection.update_one(
            {"_id": oid},
            {"$set": update_data},
        )

        if result.matched_count == 0:
            return None

        return users_collection.find_one({"_id": oid})

    @staticmethod
    def deactivate_user(user_id: str) -> bool:
        """Soft-delete: set is_active = False."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return False

        result = users_collection.update_one(
            {"_id": oid},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    @staticmethod
    def activate_user(user_id: str) -> bool:
        """Re-activate a deactivated user."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return False

        result = users_collection.update_one(
            {"_id": oid},
            {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    # ── Privilege escalation prevention ────────────────────────────────

    @staticmethod
    def validate_role_assignment(
        assigner_role: str,
        target_role: str,
    ) -> None:
        """
        Prevent privilege escalation: a user cannot assign a role
        higher than their own manageable roles allow.
        """
        manageable = get_manageable_roles(assigner_role)
        try:
            target_enum = Role.normalize(target_role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {target_role}")

        if target_enum not in manageable:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot assign role '{target_enum.display_name}'. "
                       f"You can only assign: {', '.join(r.display_name for r in manageable)}",
            )

    # ── Branch staff queries ──────────────────────────────────────────

    @staticmethod
    def get_branch_staff(branch_id: str) -> List[dict]:
        """Get all active staff assigned to a branch."""
        try:
            return list(users_collection.find({
                "branch_id": branch_id,
                "is_active": True,
                "role": {"$in": [
                    Role.BRANCH_MANAGER.value,
                    Role.KITCHEN_STAFF.value,
                    Role.DELIVERY_AGENT.value,
                ]},
            }))
        except PyMongoError as exc:
            logger.error("USER_SERVICE | get_branch_staff failed: %s", exc)
            return []

    @staticmethod
    def get_branch_staff_count(branch_id: str) -> dict:
        """Get staff count by role for a branch."""
        try:
            pipeline = [
                {"$match": {"branch_id": branch_id, "is_active": True}},
                {"$group": {"_id": "$role", "count": {"$sum": 1}}},
            ]
            results = list(users_collection.aggregate(pipeline))
            return {r["_id"]: r["count"] for r in results}
        except PyMongoError:
            return {}

    @staticmethod
    def to_response(doc: dict) -> UserResponse:
        """Convert a MongoDB user document to a safe API response."""
        return UserResponse.from_document(doc)
