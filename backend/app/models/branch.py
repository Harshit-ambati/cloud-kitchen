"""
Branch Model
--------------
Represents a physical kitchen branch location.
Each branch operates semi-independently with its own staff,
orders, and delivery agents.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BranchStatus(str, Enum):
    """Operational status of a branch."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class Branch(BaseModel):
    """
    Full branch document as stored in MongoDB.
    """
    id: Optional[str] = Field(default=None, alias="_id", description="MongoDB ObjectId or branch code (e.g. 'b1')")
    name: str = Field(..., min_length=1, max_length=100, description="Branch display name")
    address: str = Field(default="", max_length=500, description="Full street address")
    phone: str = Field(default="", max_length=20, description="Contact phone number")
    lat: float = Field(..., ge=-90, le=90, description="Branch latitude")
    lng: float = Field(..., ge=-180, le=180, description="Branch longitude")
    status: BranchStatus = Field(default=BranchStatus.ACTIVE, description="Operational status")
    service_radius_km: float = Field(default=15.0, ge=0, description="Max delivery distance in km")
    is_active: bool = Field(default=True, description="Soft-delete flag")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        use_enum_values = True


class BranchCreate(BaseModel):
    """Payload for creating a new branch."""
    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(default="", max_length=500)
    phone: str = Field(default="", max_length=20)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    status: BranchStatus = BranchStatus.ACTIVE
    service_radius_km: float = Field(default=15.0, ge=0)

    class Config:
        use_enum_values = True


class BranchUpdate(BaseModel):
    """Payload for updating an existing branch (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[BranchStatus] = None
    service_radius_km: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None

    class Config:
        use_enum_values = True
