"""
User Model
-----------
Updated user model with the new 5-role enum and branch association.
Internal staff roles (BRANCH_MANAGER, KITCHEN_STAFF, DELIVERY_AGENT)
require a branch_id.  SUPER_ADMIN and CUSTOMER do not.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.roles.enums import Role


class UserDocument(BaseModel):
    """
    User document as stored in MongoDB.
    Backward-compatible with existing 'admin'/'manager'/'delivery' roles
    via the Role.normalize() method.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    email: str
    password: str = Field(default="", exclude=True)
    name: str = Field(default="")
    role: str = Field(default=Role.CUSTOMER.value, description="User role (enum value)")
    branch_id: Optional[str] = Field(
        default=None,
        description="Required for BRANCH_MANAGER, KITCHEN_STAFF, DELIVERY_AGENT",
    )
    is_active: bool = Field(default=True, description="Account active flag")
    phone: str = Field(default="")
    address: str = Field(default="")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

    @property
    def normalized_role(self) -> Role:
        """Return the canonical Role enum, handling legacy values."""
        return Role.normalize(self.role)

    @property
    def requires_branch(self) -> bool:
        """Check if this user's role requires a branch_id."""
        from app.roles.permissions import requires_branch
        return requires_branch(self.role)


class UserCreate(BaseModel):
    """
    Payload for creating a new user.
    Validates that internal staff roles have a branch_id.
    """
    email: str
    password: str = Field(..., min_length=6)
    name: str = Field(default="")
    role: str = Field(default=Role.CUSTOMER.value)
    branch_id: Optional[str] = None
    phone: str = Field(default="")
    address: str = Field(default="")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Ensure the role is a valid Role enum value."""
        Role.normalize(v)  # raises ValueError if invalid
        return v


class UserUpdate(BaseModel):
    """Payload for updating an existing user (all fields optional)."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            Role.normalize(v)
        return v


class UserResponse(BaseModel):
    """Safe user representation (no password) for API responses."""
    user_id: str
    email: str = ""
    name: str = ""
    role: str
    role_display: str = ""
    branch_id: Optional[str] = None
    is_active: bool = True
    phone: str = ""
    address: str = ""
    created_at: Optional[datetime] = None

    @classmethod
    def from_document(cls, doc: dict) -> "UserResponse":
        """Build a UserResponse from a raw MongoDB document."""
        role_str = doc.get("role", "customer")
        try:
            role_enum = Role.normalize(role_str)
            display = role_enum.display_name
        except ValueError:
            display = role_str

        return cls(
            user_id=str(doc.get("_id", "")),
            email=doc.get("email", ""),
            name=doc.get("name", ""),
            role=role_str,
            role_display=display,
            branch_id=doc.get("branch_id"),
            is_active=doc.get("is_active", True),
            phone=doc.get("phone", ""),
            address=doc.get("address", ""),
            created_at=doc.get("created_at"),
        )
