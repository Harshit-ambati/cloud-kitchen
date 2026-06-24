"""
Auth Dependencies
-------------------
FastAPI dependency injection functions for authentication and
role-based access control.

Updated to use the canonical 5-role enum system while maintaining
full backward compatibility with legacy role strings.
"""

import logging
from typing import Optional

from bson.objectid import ObjectId
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from app.db import db
from app.auth.jwt import decode_token
from app.roles.enums import Role

logger = logging.getLogger(__name__)

users_collection = db["users"]


class UserLogin(BaseModel):
    email: str
    password: str


class CurrentUser(BaseModel):
    """
    Authenticated user context passed through FastAPI dependencies.
    Available in route handlers via Depends(get_current_user).
    """
    user_id: str
    email: str = ""
    username: str = ""
    role: str
    role_display: str = ""
    branch_id: Optional[str] = None
    name: str = ""
    phone: str = ""
    is_active: bool = True

    @property
    def normalized_role(self) -> Role:
        """Return the canonical Role enum, handling legacy values."""
        return Role.normalize(self.role)

    @property
    def is_super_admin(self) -> bool:
        return self.normalized_role == Role.SUPER_ADMIN

    @property
    def is_branch_manager(self) -> bool:
        return self.normalized_role == Role.BRANCH_MANAGER

    @property
    def is_kitchen_staff(self) -> bool:
        return self.normalized_role == Role.KITCHEN_STAFF

    @property
    def is_delivery_agent(self) -> bool:
        return self.normalized_role == Role.DELIVERY_AGENT

    @property
    def is_customer(self) -> bool:
        return self.normalized_role == Role.CUSTOMER

    @property
    def is_branch_scoped(self) -> bool:
        """True if this user's data should be filtered by branch_id."""
        return self.normalized_role in (Role.BRANCH_MANAGER, Role.KITCHEN_STAFF)


def object_id_or_none(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None


def normalize_user(document: dict) -> CurrentUser:
    """Build a CurrentUser from a raw MongoDB user document."""
    role_raw = document.get("role", "customer")

    # Normalize role — accept legacy values
    try:
        role_enum = Role.normalize(role_raw)
        role_display = role_enum.display_name
    except ValueError:
        raise HTTPException(status_code=403, detail=f"Unknown role: {role_raw}")

    # Branch validation — managers, kitchen staff, delivery agents need branch_id
    branch_id = document.get("branch_id")
    from app.roles.permissions import requires_branch
    if requires_branch(role_enum) and not branch_id:
        # For legacy data, log warning but don't block
        logger.warning(
            "RBAC_WARN | User %s has role %s but no branch_id assigned",
            document.get("_id"), role_raw,
        )

    # Check active status
    is_active = document.get("is_active", True)

    return CurrentUser(
        user_id=str(document["_id"]),
        email=document.get("email", ""),
        username=document.get("username") or document.get("email", ""),
        role=role_enum.value,  # Always store canonical value
        role_display=role_display,
        branch_id=branch_id,
        name=document.get("name", ""),
        phone=document.get("phone", ""),
        is_active=is_active,
    )


def find_user_by_id(user_id: str):
    parsed_user_id = object_id_or_none(user_id)
    queries = []
    if parsed_user_id is not None:
        queries.append({"_id": parsed_user_id})
    queries.append({"user_id": user_id})

    for query in queries:
        user = users_collection.find_one(query)
        if user:
            return user
    return None


async def get_current_user(request: Request) -> CurrentUser:
    """
    Extract and validate the current user from the Authorization header.
    Falls back to JWT claims if the database is unreachable.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user_id")

    try:
        user = find_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return normalize_user(user)
    except HTTPException:
        raise
    except PyMongoError as exc:
        # ── Graceful degradation — trust JWT claims when DB is down ──
        logger.warning(
            "DB_FALLBACK | User lookup failed for %s, falling back to JWT claims: %s",
            user_id, exc,
        )
        role = payload.get("role", "customer")
        try:
            role_enum = Role.normalize(role)
            role_display = role_enum.display_name
        except ValueError:
            role_display = role

        return CurrentUser(
            user_id=user_id,
            role=role,
            role_display=role_display,
            branch_id=payload.get("branch_id"),
            phone=payload.get("phone", ""),
        )


# ── Optional auth (for public endpoints that benefit from user context) ──

async def get_current_user_optional(request: Request) -> Optional[CurrentUser]:
    """
    Like get_current_user, but returns None instead of raising 401
    when no token is present. Useful for public endpoints that
    optionally personalize responses for logged-in users.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# ── Legacy role check dependencies ───────────────────────────────────
# These are kept for backward compatibility with existing routes.
# New routes should use require_permissions() from app.middleware.rbac

def require_role(*allowed_roles: str):
    """Generic role-checking dependency factory."""
    def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        # Normalize the user's role for comparison
        try:
            user_role = Role.normalize(current_user.role)
        except ValueError:
            raise HTTPException(status_code=403, detail=f"Unknown role: {current_user.role}")

        # Build set of allowed normalized roles
        allowed_normalized = set()
        for r in allowed_roles:
            try:
                allowed_normalized.add(Role.normalize(r))
            except ValueError:
                continue

        # SUPER_ADMIN always passes
        if user_role == Role.SUPER_ADMIN:
            return current_user

        if user_role not in allowed_normalized:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Require SUPER_ADMIN role."""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_manager(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Require BRANCH_MANAGER role. SUPER_ADMIN also passes."""
    if current_user.is_super_admin:
        return current_user
    if not current_user.is_branch_manager:
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user


def require_delivery(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Require DELIVERY_AGENT role."""
    if not current_user.is_delivery_agent:
        raise HTTPException(status_code=403, detail="Delivery/Agent access required")
    return current_user


# ── Query filter builders ─────────────────────────────────────────────
# These build MongoDB query filters that enforce branch/ownership isolation.

def scoped_query(scope: dict, extra: Optional[dict] = None) -> dict:
    if not scope:
        return dict(extra or {})
    if not extra:
        return dict(scope)
    return {"$and": [dict(scope), dict(extra)]}


def delivery_assignment_filter(user_id: str) -> dict:
    return {
        "$or": [
            {"assigned_delivery_id": user_id},
            {"assigned_agent_id": user_id},
        ]
    }


def build_order_filter(user: CurrentUser, extra: Optional[dict] = None) -> dict:
    """Build a MongoDB order query scoped by role."""
    scope: dict = {}

    if user.is_super_admin:
        pass  # no filter — sees everything
    elif user.is_branch_manager or user.is_kitchen_staff:
        scope["branch_id"] = user.branch_id
    elif user.is_delivery_agent:
        scope = delivery_assignment_filter(user.user_id)
    elif user.is_customer:
        scope["customer_user_id"] = user.user_id
    else:
        scope["_id"] = None  # deny all for unknown roles

    return scoped_query(scope, extra)


def build_agent_filter(user: CurrentUser, extra: Optional[dict] = None) -> dict:
    """Build a MongoDB agent query scoped by role."""
    scope: dict = {}

    if user.is_super_admin:
        pass  # no filter
    elif user.is_branch_manager or user.is_kitchen_staff:
        scope["branch_id"] = user.branch_id
    elif user.is_delivery_agent:
        identity_filter = [{"user_id": user.user_id}]
        parsed_user_id = object_id_or_none(user.user_id)
        if parsed_user_id is not None:
            identity_filter.append({"_id": parsed_user_id})
        scope = {"$or": identity_filter}
    else:
        scope["_id"] = None  # deny

    return scoped_query(scope, extra)


def build_user_filter(user: CurrentUser, extra: Optional[dict] = None) -> dict:
    """Build a MongoDB user query scoped by role."""
    scope: dict = {}

    if user.is_super_admin:
        pass  # no filter
    elif user.is_branch_manager:
        scope["branch_id"] = user.branch_id
    else:
        # Everyone else can only see themselves
        identity_filter = [{"user_id": user.user_id}]
        parsed_user_id = object_id_or_none(user.user_id)
        if parsed_user_id is not None:
            identity_filter.append({"_id": parsed_user_id})
        scope = {"$or": identity_filter}

    return scoped_query(scope, extra)


def log_access(user: CurrentUser, resource: str, records_returned: int):
    logger.info(
        "RBAC_ACCESS | user_role=%s | branch_id=%s | resource=%s | records_returned=%d",
        user.role,
        user.branch_id or "all",
        resource,
        records_returned,
    )
