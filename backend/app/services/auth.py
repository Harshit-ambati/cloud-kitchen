import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException
from pymongo.errors import PyMongoError

from app.db import db

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "cloud-kitchen-secret-key-change-in-production-please-change")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
users_collection = db["users"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRY_HOURS))
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def authenticate_user(email: str, password: str) -> dict:
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

    return user


def create_user_token(user: dict) -> str:
    return create_access_token(
        {
            "user_id": str(user["_id"]),
            "role": user["role"],
            "branch_id": user.get("branch_id"),
        }
    )
