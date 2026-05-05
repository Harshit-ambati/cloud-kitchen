import logging
from typing import Literal, Optional

from bson.objectid import ObjectId
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from app.db import db
from app.services.auth import decode_token


logger = logging.getLogger(__name__)

Role = Literal["admin", "manager", "delivery"]
users_collection = db["users"]


class UserLogin(BaseModel):
    email: str
    password: str


class CurrentUser(BaseModel):
    user_id: str
    email: str = ""
    username: str = ""
    role: str
    branch_id: Optional[str] = None
    name: str = ""


def object_id_or_none(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None


def normalize_user(document: dict) -> CurrentUser:
    role = document.get("role", "admin")
    if role not in ("admin", "manager", "delivery", "agent"):
        raise HTTPException(status_code=403, detail=f"Unknown role: {role}")

    branch_id = document.get("branch_id")
    if role == "manager" and not branch_id:
        raise HTTPException(status_code=403, detail="Manager users must have a branch_id")

    return CurrentUser(
        user_id=str(document["_id"]),
        email=document.get("email", ""),
        username=document.get("username") or document.get("email", ""),
        role=role,
        branch_id=branch_id,
        name=document.get("name", ""),
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
        # ── Graceful degradation — guardrails ─────────────────────
        # Safe to trust the JWT claims here because:
        #   1. decode_token() already verified the signature AND
        #      rejected expired tokens (jwt.ExpiredSignatureError)
        #      before this function was reached.
        #   2. The fallback only fires on PyMongoError (DB down),
        #      NOT on "user not found" (which is an HTTPException
        #      re-raised above).
        #
        # TODO: Add a `token_version` integer field to the users
        #       collection.  Include it in the JWT payload at login.
        #       When the DB is reachable, compare payload.token_version
        #       against the stored value to support instant token
        #       revocation (password change, role change, ban).
        logger.warning(
            "DB_FALLBACK | User lookup failed for %s, falling back to JWT claims: %s",
            user_id, exc,
        )
        role = payload.get("role", "admin")
        return CurrentUser(
            user_id=user_id,
            role=role,
            branch_id=payload.get("branch_id"),
        )


def require_role(*allowed_roles: str):
    def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def require_manager(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user

def require_delivery(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role not in ("delivery", "agent"):
        raise HTTPException(status_code=403, detail="Delivery/Agent access required")
    return current_user


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
    scope: dict = {}

    if user.role == "manager":
        scope["branch_id"] = user.branch_id
    elif user.role in ("delivery", "agent"):
        scope = delivery_assignment_filter(user.user_id)

    return scoped_query(scope, extra)


def build_agent_filter(user: CurrentUser, extra: Optional[dict] = None) -> dict:
    scope: dict = {}

    if user.role == "manager":
        scope["branch_id"] = user.branch_id
    elif user.role in ("delivery", "agent"):
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
