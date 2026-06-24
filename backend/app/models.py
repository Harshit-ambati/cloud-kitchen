"""
Backward Compatibility Shim
-----------------------------
Re-exports all models from the new models/ package so that
existing imports like `from app.models import OrderCreate`
continue to work without changes.

All models are now defined in app/models/ submodules.
"""

# flake8: noqa: F401
from app.models.order import OrderItem, OrderCreate, OrderStatusUpdate
from app.models.agent import AgentCreate, AgentUpdate
from app.models.assignment import AssignmentRequest, AssignmentResult
from app.models.user import UserDocument, UserCreate, UserUpdate, UserResponse
from app.models.branch import Branch, BranchCreate, BranchUpdate, BranchStatus
