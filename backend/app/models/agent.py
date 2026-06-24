"""
Agent Models
--------------
Pydantic schemas for delivery agent creation and updates.
Unchanged from original — preserved for backward compatibility.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    available: bool = True


class AgentUpdate(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    available: Optional[bool] = None
