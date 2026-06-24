"""
Models Package
---------------
Centralised data models for the Cloud Kitchen platform.

Re-exports all models so consumers can do:
    from app.models import Branch, UserDocument, OrderCreate, ...
"""

from app.models.branch import Branch, BranchCreate, BranchUpdate, BranchStatus
from app.models.user import UserDocument, UserCreate, UserUpdate, UserResponse
from app.models.order import OrderItem, OrderCreate, OrderStatusUpdate
from app.models.agent import AgentCreate, AgentUpdate
from app.models.assignment import AssignmentRequest, AssignmentResult

__all__ = [
    # Branch
    "Branch",
    "BranchCreate",
    "BranchUpdate",
    "BranchStatus",
    # User
    "UserDocument",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Order
    "OrderItem",
    "OrderCreate",
    "OrderStatusUpdate",
    # Agent
    "AgentCreate",
    "AgentUpdate",
    # Assignment
    "AssignmentRequest",
    "AssignmentResult",
]
