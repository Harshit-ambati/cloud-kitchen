"""
JWT Token Management
----------------------
Token creation and decoding with configurable secret and expiry.
Uses centralised settings from app.config.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_EXPIRY_HOURS = settings.JWT_EXPIRY_HOURS


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    The payload includes:
        - user_id: MongoDB ObjectId as string
        - role: canonical role string (e.g. 'super_admin')
        - branch_id: optional branch association
        - exp: expiration timestamp
    """
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRY_HOURS))
    payload["iat"] = datetime.utcnow()
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises HTTPException on expired or invalid tokens.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
