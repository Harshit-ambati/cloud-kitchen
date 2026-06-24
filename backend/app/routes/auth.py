"""
Auth Routes
--------------
Registration, login, and user profile endpoints.
Updated to use the new 5-role system.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from pymongo.errors import PyMongoError

from app.dependencies.auth import UserLogin, users_collection, get_current_user, CurrentUser
from app.services.auth import authenticate_user, create_user_token, hash_password
from app.auth.schemas import GmailLogin, OtpRequest, OtpVerify, UserRegister
from app.roles.enums import Role
from app.roles.permissions import requires_branch
from app.models.user import UserResponse
from app.services.otp import request_otp, verify_otp

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister):
    """
    Register a new user.
    Validates:
        - Role is a valid enum value
        - Internal staff roles have a branch_id
        - Email is unique
    """
    try:
        # Validate role
        try:
            role_enum = Role.normalize(payload.role)
            # Public registration is strictly limited to customers
            if role_enum != Role.CUSTOMER:
                raise HTTPException(
                    status_code=403,
                    detail="Public registration is limited to customer accounts. Staff accounts must be created internally."
                )
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {payload.role}")

        # Validate branch_id requirement (though CUSTOMER doesn't require it, keeping logic for safety)
        if requires_branch(role_enum) and not payload.branch_id:
            raise HTTPException(
                status_code=400,
                detail=f"Role '{role_enum.display_name}' requires a branch_id",
            )

        # Check duplicate email
        if users_collection.find_one({"email": payload.email}):
            raise HTTPException(status_code=400, detail="User with this email already exists")

        new_user = {
            "email": payload.email,
            "password": hash_password(payload.password),
            "role": payload.role,
            "branch_id": payload.branch_id,
            "name": payload.name,
            "phone": payload.phone,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = users_collection.insert_one(new_user)
        return {
            "message": "User registered successfully",
            "user_id": str(result.inserted_id),
            "role": payload.role,
            "role_display": role_enum.display_name,
        }
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | register failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.post("/login")
def login(payload: UserLogin):
    """
    Authenticate and return a JWT access token.
    Response includes role metadata for frontend dashboard routing.
    """
    try:
        user = authenticate_user(payload.email, payload.password)

        role_str = user.get("role", "customer")
        try:
            role_enum = Role.normalize(role_str)
            role_display = role_enum.display_name
        except ValueError:
            role_display = role_str

        return {
            "access_token": create_user_token(user),
            "token_type": "bearer",
            "role": role_str,
            "role_display": role_display,
            "user_id": str(user["_id"]),
            "branch_id": user.get("branch_id"),
        }
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | login failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.post("/otp/request")
def request_checkout_otp(payload: OtpRequest):
    """Request an OTP for customer checkout login."""
    try:
        return request_otp(payload.phone)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | otp request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.post("/otp/verify")
def verify_checkout_otp(payload: OtpVerify):
    """Verify a checkout OTP and return a customer JWT."""
    try:
        return verify_otp(payload.phone, payload.otp, name=payload.name)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | otp verify failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.post("/gmail/login")
def gmail_customer_login(payload: GmailLogin):
    """
    Local Gmail-style customer login.
    This is intentionally limited to customer accounts and can be replaced
    by real Google OAuth later without changing the frontend flow.
    """
    email = payload.email.strip().lower()
    if not email.endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Please use a Gmail address")

    try:
        existing_user = users_collection.find_one({"email": email})
        now = datetime.utcnow()

        if existing_user:
            try:
                role_enum = Role.normalize(existing_user.get("role", Role.CUSTOMER.value))
            except ValueError:
                raise HTTPException(status_code=403, detail="This account cannot be used for customer login")

            if role_enum != Role.CUSTOMER:
                raise HTTPException(status_code=403, detail="Staff accounts must use the operations login")

            updates = {"updated_at": now, "auth_provider": "gmail"}
            if payload.name and not existing_user.get("name"):
                updates["name"] = payload.name
            users_collection.update_one({"_id": existing_user["_id"]}, {"$set": updates})
            user = users_collection.find_one({"_id": existing_user["_id"]})
        else:
            user = {
                "email": email,
                "password": "",
                "role": Role.CUSTOMER.value,
                "branch_id": None,
                "name": payload.name or email.split("@", 1)[0],
                "phone": "",
                "is_active": True,
                "auth_provider": "gmail",
                "created_at": now,
                "updated_at": now,
            }
            result = users_collection.insert_one(user)
            user["_id"] = result.inserted_id

        return {
            "access_token": create_user_token(user),
            "token_type": "bearer",
            "role": Role.CUSTOMER.value,
            "role_display": Role.CUSTOMER.display_name,
            "user_id": str(user["_id"]),
            "branch_id": None,
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "phone": user.get("phone", ""),
        }
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | gmail customer login failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Return the current user's profile."""
    return current_user.dict()


@router.get("/roles")
def get_available_roles():
    """
    Return all available roles with display names.
    Useful for admin dashboards and registration forms.
    """
    # Only return canonical (non-legacy) roles
    canonical_roles = [
        Role.SUPER_ADMIN,
        Role.BRANCH_MANAGER,
        Role.KITCHEN_STAFF,
        Role.DELIVERY_AGENT,
        Role.CUSTOMER,
    ]
    return {
        "roles": [
            {
                "value": role.value,
                "display_name": role.display_name,
                "requires_branch": requires_branch(role),
            }
            for role in canonical_roles
        ]
    }
