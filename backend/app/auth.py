from typing import Literal, Optional

from pydantic import BaseModel

from app.dependencies.auth import (
    CurrentUser,
    build_agent_filter,
    build_order_filter,
    get_current_user,
    log_access,
    require_admin,
    require_delivery,
    require_manager,
    users_collection,
)
from app.services.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class UserRegister(BaseModel):
    email: str
    password: str
    role: Literal["admin", "manager", "delivery", "agent"] = "admin"
    branch_id: Optional[str] = None
    name: str = ""


class LegacyUserLogin(BaseModel):
    username: str
    password: str


UserLogin = LegacyUserLogin
decode_access_token = decode_token

