"""
Backward Compatibility Shim — Auth
-------------------------------------
Re-exports all auth symbols from their new locations so that
existing imports like:
    from app.auth import CurrentUser, get_current_user, ...
continue to work.

New code should import from:
    - app.auth.jwt (JWT operations)
    - app.auth.password (hashing)
    - app.auth.schemas (request/response models)
    - app.dependencies.auth (FastAPI dependencies)
    - app.roles (Role, Permission enums)
"""

# flake8: noqa: F401

from app.dependencies.auth import (
    CurrentUser,
    build_agent_filter,
    build_order_filter,
    build_user_filter,
    get_current_user,
    get_current_user_optional,
    log_access,
    require_admin,
    require_delivery,
    require_manager,
    users_collection,
)
from app.auth.jwt import create_access_token, decode_token
from app.auth.password import hash_password, verify_password
from app.auth.schemas import UserRegister, UserLogin, LegacyUserLogin, TokenResponse

# Legacy aliases
decode_access_token = decode_token
