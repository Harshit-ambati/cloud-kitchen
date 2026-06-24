"""
Auth Package
--------------
Authentication services, JWT handling, and password management.

This package provides:
    - JWT token creation / validation
    - Password hashing and verification
    - Auth request/response schemas
    - Future: OAuth2, token refresh, revocation
"""

from app.auth.jwt import (
    create_access_token,
    decode_token,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS,
)
from app.auth.password import hash_password, verify_password
from app.auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    LegacyUserLogin,
)

__all__ = [
    "create_access_token",
    "decode_token",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "JWT_EXPIRY_HOURS",
    "hash_password",
    "verify_password",
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "LegacyUserLogin",
]
