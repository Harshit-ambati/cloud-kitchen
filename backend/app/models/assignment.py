"""
Assignment Models
-------------------
Pydantic schemas for the order-to-agent assignment workflow.
Unchanged from original — preserved for backward compatibility.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class AssignmentRequest(BaseModel):
    order_ids: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None
    auto_update_status: bool = True
    respect_availability: bool = True


class AssignmentResult(BaseModel):
    agent_id: str
    order_ids: List[str] = Field(default_factory=list)
