"""
Auth Request/Response Schemas
-------------------------------
Pydantic models for auth-related API payloads.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.roles.enums import Role


class UserRegister(BaseModel):
    """Registration payload — supports the new 5-role system."""
    email: str
    password: str = Field(..., min_length=6)
    role: str = Field(default=Role.CUSTOMER.value)
    branch_id: Optional[str] = None
    name: str = ""
    phone: str = ""


class UserLogin(BaseModel):
    """Login payload — accepts email + password."""
    email: str
    password: str


class LegacyUserLogin(BaseModel):
    """
    Legacy login payload — accepts 'username' field.
    Kept for backward compatibility with older frontends.
    """
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response after successful login."""
    access_token: str
    token_type: str = "bearer"
    role: str
    role_display: str = ""
    user_id: str
    branch_id: Optional[str] = None
    expires_in_hours: int = 24


class OtpRequest(BaseModel):
    """Request a phone OTP for customer checkout login."""
    phone: str = Field(..., min_length=8, max_length=20)
    name: str = ""


class OtpVerify(BaseModel):
    """Verify a phone OTP and receive a customer JWT."""
    phone: str = Field(..., min_length=8, max_length=20)
    otp: str = Field(..., min_length=4, max_length=8)
    name: str = ""


class GmailLogin(BaseModel):
    """Local Gmail-style customer login until Google OAuth is connected."""
    email: str = Field(..., min_length=6, max_length=254)
    name: str = ""
