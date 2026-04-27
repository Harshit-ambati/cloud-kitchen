from typing import List, Optional

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    dish_id: str
    name: str
    category: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    line_total: float = Field(ge=0)


class OrderCreate(BaseModel):
    user_lat: float
    user_lng: float
    kitchen_lat: float
    kitchen_lng: float
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


class OrderStatusUpdate(BaseModel):
    status: str


class AgentCreate(BaseModel):
    name: str
    lat: float
    lng: float
    available: bool = True


class AgentUpdate(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    available: Optional[bool] = None


class AssignmentRequest(BaseModel):
    order_ids: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None
    auto_update_status: bool = True
    respect_availability: bool = True


class AssignmentResult(BaseModel):
    agent_id: str
    order_ids: List[str] = Field(default_factory=list)
