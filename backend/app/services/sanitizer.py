"""
Order Sanitizer — Safe Optimizer Contract
-------------------------------------------
Transforms raw MongoDB documents into validated DTOs before they
reach the route optimizer.  Invalid records are dropped and logged
so the optimizer never receives malformed data.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class ValidOrderDTO(BaseModel):
    """
    Minimum viable order shape required by the optimizer.
    Any document that fails validation against this schema is
    dropped before it reaches optimize_routes().
    """
    id: str
    user_lat: float = Field(ge=-90, le=90)
    user_lng: float = Field(ge=-180, le=180)
    kitchen_lat: float = Field(ge=-90, le=90)
    kitchen_lng: float = Field(ge=-180, le=180)
    status: str
    fulfillment_mode: str = "delivery"
    order_type: str = "regular"
    priority: str = "standard"
    distance_km: float = 0.0
    predicted_prep_minutes: float = 0.0
    predicted_travel_minutes: float = 0.0
    predicted_eta_minutes: float = 0.0
    customer_name: str = "Guest"
    items: list = Field(default_factory=list)
    item_count: int = 0
    subtotal: float = 0.0
    delivery_fee: float = 0.0
    total_amount: float = 0.0


class ValidAgentDTO(BaseModel):
    """Minimum viable agent shape required by the optimizer."""
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    available: bool = True
    current_load: int = 0
    active_order_ids: list = Field(default_factory=list)


def sanitize_orders_for_optimizer(
    serialized_orders: list[dict],
) -> tuple[list[dict], int]:
    """
    Validate a list of already-serialized order dicts against
    ValidOrderDTO.  Returns (valid_dtos, skipped_count).

    Each valid DTO is returned as a plain dict so the optimizer's
    existing interface is unchanged.
    """
    valid = []
    skipped = 0
    for order in serialized_orders:
        try:
            dto = ValidOrderDTO(**order)
            valid.append(dto.dict())
        except ValidationError as exc:
            skipped += 1
            logger.warning(
                "SANITIZER | Dropped order %s before optimizer: %s",
                order.get("id", "?"), exc.errors(),
            )
    return valid, skipped


def sanitize_agents_for_optimizer(
    raw_agent_docs: list[dict],
) -> tuple[list[dict], int]:
    """
    Validate raw agent documents.  Returns (valid_dtos, skipped_count).
    """
    valid = []
    skipped = 0
    for agent in raw_agent_docs:
        try:
            dto = ValidAgentDTO(**agent)
            valid.append(dto.dict())
        except ValidationError as exc:
            skipped += 1
            logger.warning(
                "SANITIZER | Dropped agent %s before optimizer: %s",
                agent.get("id", "?"), exc.errors(),
            )
    return valid, skipped
