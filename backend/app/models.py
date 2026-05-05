from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    dish_id: str
    name: str
    category: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    line_total: float = Field(ge=0)


class OrderCreate(BaseModel):
    user_lat: float = Field(..., ge=-90, le=90, description="Latitude must be between -90 and 90")
    user_lng: float = Field(..., ge=-180, le=180, description="Longitude must be between -180 and 180")
    kitchen_lat: float = Field(..., ge=-90, le=90)
    kitchen_lng: float = Field(..., ge=-180, le=180)
    fulfillment_mode: str = "delivery"
    order_type: str = "regular"
    priority: str = "standard"
    customer_name: str = "Guest"
    customer_phone: str = ""
    delivery_area: str = ""
    delivery_address: str = ""
    restaurant_name: str = "Cloud Kitchen"
    items: List[OrderItem] = Field(default_factory=list)
    item_count: int = 0
    subtotal: float = Field(default=0, ge=0)
    delivery_fee: float = Field(default=0, ge=0)
    platform_fee: float = Field(default=0, ge=0)
    taxes: float = Field(default=0, ge=0)
    total_amount: float = Field(default=0, ge=0)
    is_simulated: bool = Field(default=False, description="True for synthetic/test orders")


class OrderStatusUpdate(BaseModel):
    status: str


class AgentCreate(BaseModel):
    name: str
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    available: bool = True


class AgentUpdate(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    available: Optional[bool] = None


class AssignmentRequest(BaseModel):
    order_ids: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None
    auto_update_status: bool = True
    respect_availability: bool = True


class AssignmentResult(BaseModel):
    agent_id: str
    order_ids: List[str] = Field(default_factory=list)


class UserDocument(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: str
    password: str
    role: Literal["admin", "manager", "delivery"]
    branch_id: Optional[str] = None
