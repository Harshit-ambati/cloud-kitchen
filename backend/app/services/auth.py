"""
Backward Compatibility Shim — Services Auth
----------------------------------------------
Re-exports from new locations so existing imports work.
All new code should import from app.auth.* directly.
"""

# flake8: noqa: F401

import logging
from typing import Optional

from fastapi import HTTPException
from pymongo.errors import PyMongoError

from app.auth.jwt import (
    create_access_token,
    decode_token,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS,
)
from app.auth.password import hash_password, verify_password
from app.db import db
from app.roles.enums import Role

logger = logging.getLogger(__name__)

users_collection = db["users"]


def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate a user by email and password.
    Returns the raw MongoDB document on success.
    """
    try:
        user = users_collection.find_one({"email": email})
    except PyMongoError as exc:
        logger.error("DB_ERROR | authenticate_user DB lookup failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        ) from exc

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    stored_password = user.get("password") or user.get("password_hash")
    if not verify_password(password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact support.")

    return user


def create_user_token(user: dict) -> str:
    """Create a JWT token from a user document."""
    role_str = user.get("role", "customer")

    # Normalize to canonical value
    try:
        role_enum = Role.normalize(role_str)
        role_display = role_enum.display_name
        canonical_role = role_enum.value
    except ValueError:
        role_display = role_str
        canonical_role = role_str

    return create_access_token(
        {
            "user_id": str(user["_id"]),
            "role": canonical_role,
            "branch_id": user.get("branch_id"),
            "role_display": role_display,
            "phone": user.get("phone", ""),
            "name": user.get("name", ""),
        }
    )
