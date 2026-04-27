from datetime import datetime, timedelta
from typing import Optional

from bson.objectid import ObjectId
from fastapi import APIRouter, HTTPException

from app.db import agents, orders
from app.models import AssignmentRequest, OrderCreate, OrderStatusUpdate
from app.services.distance import haversine
from app.services.optimizer import assign_orders
from ml.predict_eta import predict_eta

router = APIRouter()


VALID_STATUSES = ["placed", "accepted", "in_transit", "delivered", "ready_for_pickup", "collected", "cancelled"]
DELIVERY_STATUS_TRANSITIONS = {
    "placed": {"accepted", "cancelled"},
    "accepted": {"in_transit", "cancelled"},
    "in_transit": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}
TAKEAWAY_STATUS_TRANSITIONS = {
    "placed": {"accepted", "cancelled"},
    "accepted": {"ready_for_pickup", "cancelled"},
    "ready_for_pickup": {"collected", "cancelled"},
    "collected": set(),
    "cancelled": set(),
}


def serialize_order(order):
    return {
        "id": str(order["_id"]),
        "user_lat": order["user_lat"],
        "user_lng": order["user_lng"],
        "kitchen_lat": order["kitchen_lat"],
        "kitchen_lng": order["kitchen_lng"],
        "fulfillment_mode": order.get("fulfillment_mode", "delivery"),
        "order_type": order["order_type"],
        "priority": order.get("priority", "standard"),
        "customer_name": order.get("customer_name", "Guest"),
        "customer_phone": order.get("customer_phone", ""),
        "delivery_area": order.get("delivery_area", ""),
        "delivery_address": order.get("delivery_address", ""),
        "restaurant_name": order.get("restaurant_name", "Cloud Kitchen"),
        "items": order.get("items", []),
        "item_count": order.get("item_count", 0),
        "subtotal": round(order.get("subtotal", 0), 2),
        "delivery_fee": round(order.get("delivery_fee", 0), 2),
        "platform_fee": round(order.get("platform_fee", 0), 2),
        "taxes": round(order.get("taxes", 0), 2),
        "total_amount": round(order.get("total_amount", 0), 2),
        "status": order["status"],
        "prep_status": order.get("prep_status", "queued"),
        "assignment_status": order.get("assignment_status", "unassigned"),
        "assigned_agent_id": order.get("assigned_agent_id"),
        "assigned_agent_name": order.get("assigned_agent_name"),
        "distance_km": round(order.get("distance_km", 0), 2),
        "predicted_prep_minutes": order.get("predicted_prep_minutes", 0),
        "predicted_travel_minutes": order.get("predicted_travel_minutes", 0),
        "predicted_eta_minutes": order.get("predicted_eta_minutes", 0),
        "pickup_ready_at": order.get("pickup_ready_at"),
        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at"),
    }


def parse_object_id(value, resource_name):
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {resource_name} id") from exc


def get_allowed_status_transitions(order):
    if order.get("fulfillment_mode", "delivery") == "takeaway":
        return TAKEAWAY_STATUS_TRANSITIONS

    return DELIVERY_STATUS_TRANSITIONS


def sync_agent_load(agent_id):
    active_statuses = ["accepted", "in_transit"]
    active_order_ids = [
        str(order["_id"])
        for order in orders.find(
            {"assigned_agent_id": agent_id, "status": {"$in": active_statuses}}
        )
    ]
    agents.update_one(
        {"_id": ObjectId(agent_id)},
        {
            "$set": {
                "active_order_ids": active_order_ids,
                "current_load": len(active_order_ids),
                "available": len(active_order_ids) == 0,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def increment_agent_delivery_stats(agent_id):
    agents.update_one(
        {"_id": ObjectId(agent_id)},
        {
            "$inc": {"total_deliveries": 1},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )


@router.post("/create")
def create_order(order: OrderCreate):
    """Create a new order with ETA calculation"""
    try:
        data = order.dict()
        items = data.get("items", [])
        fulfillment_mode = data.get("fulfillment_mode", "delivery")

        distance = haversine(
            data["user_lat"],
            data["user_lng"],
            data["kitchen_lat"],
            data["kitchen_lng"]
        )

        travel_eta = predict_eta(distance) if fulfillment_mode == "delivery" else 0
        prep_eta = 12 if data["order_type"] == "express" else 18
        if items:
            prep_eta += min(len(items) * 2, 10)

        if fulfillment_mode == "takeaway":
            data["delivery_fee"] = 0
            data["delivery_area"] = "Restaurant pickup"
            data["delivery_address"] = "Collect from Cloud Kitchen Express, Hyderabad"

        if items and data.get("item_count", 0) <= 0:
            data["item_count"] = sum(item.get("quantity", 0) for item in items)
        if items and data.get("subtotal", 0) <= 0:
            data["subtotal"] = round(sum(item.get("line_total", 0) for item in items), 2)
        if data.get("total_amount", 0) <= 0:
            data["total_amount"] = round(
                data.get("subtotal", 0)
                + data.get("delivery_fee", 0)
                + data.get("platform_fee", 0)
                + data.get("taxes", 0),
                2,
            )

        data["distance_km"] = distance
        data["predicted_travel_minutes"] = travel_eta
        data["predicted_prep_minutes"] = prep_eta
        data["predicted_eta_minutes"] = round(prep_eta + travel_eta, 2)
        data["status"] = "placed"
        data["prep_status"] = "queued"
        data["assignment_status"] = "unassigned"
        data["assigned_agent_id"] = None
        data["assigned_agent_name"] = None
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = data["created_at"]
        data["pickup_ready_at"] = (
            data["created_at"] + timedelta(minutes=prep_eta) if fulfillment_mode == "takeaway" else None
        )

        result = orders.insert_one(data)
        created_order = orders.find_one({"_id": result.inserted_id})
        return serialize_order(created_order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def get_all_orders():
    """Get all orders"""
    all_orders = [serialize_order(order) for order in orders.find().sort("created_at", -1)]
    return {"orders": all_orders, "count": len(all_orders)}

@router.get("/{order_id}")
def get_order(order_id: str):
    """Get a specific order by ID"""
    try:
        order = orders.find_one({"_id": parse_object_id(order_id, "order")})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return serialize_order(order)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{order_id}/status")
def update_order_status(order_id: str, status_update: OrderStatusUpdate):
    """Update order status"""
    status = status_update.status

    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")

    try:
        existing_order = orders.find_one({"_id": parse_object_id(order_id, "order")})
        if not existing_order:
            raise HTTPException(status_code=404, detail="Order not found")

        current_status = existing_order["status"]
        if status == current_status:
            raise HTTPException(status_code=400, detail=f"Order is already {status}")

        allowed_status_transitions = get_allowed_status_transitions(existing_order)
        if status not in allowed_status_transitions.get(current_status, set()):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition order from {current_status} to {status}",
            )

        prep_status = existing_order.get("prep_status", "queued")
        assignment_status = existing_order.get("assignment_status", "unassigned")

        if status == "accepted":
            prep_status = "preparing"
            assignment_status = (
                "assigned"
                if existing_order.get("fulfillment_mode", "delivery") == "delivery"
                else "pickup_pending"
            )
        elif status == "in_transit":
            prep_status = "ready"
        elif status == "ready_for_pickup":
            prep_status = "ready"
            assignment_status = "pickup_ready"
        elif status == "delivered":
            prep_status = "completed"
        elif status == "collected":
            prep_status = "completed"
            assignment_status = "collected"
        elif status == "cancelled":
            prep_status = "cancelled"
            assignment_status = "cancelled"

        result = orders.update_one(
            {"_id": parse_object_id(order_id, "order")},
            {
                "$set": {
                    "status": status,
                    "prep_status": prep_status,
                    "assignment_status": assignment_status,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Order not found")

        updated_order = orders.find_one({"_id": parse_object_id(order_id, "order")})
        if updated_order.get("assigned_agent_id"):
            if status == "delivered" and current_status != "delivered":
                increment_agent_delivery_stats(updated_order["assigned_agent_id"])
            sync_agent_load(updated_order["assigned_agent_id"])

        return serialize_order(updated_order)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/optimize-assignments")
def optimize_assignments(request: Optional[AssignmentRequest] = None):
    """Optimize and assign orders to agents"""
    try:
        request = request or AssignmentRequest()
        order_query = {"status": "placed", "fulfillment_mode": "delivery"}
        if request.order_ids:
            order_query = {
                "_id": {"$in": [parse_object_id(order_id, "order") for order_id in request.order_ids]},
                "status": "placed",
                "fulfillment_mode": "delivery",
            }

        agent_query = {}
        if request.agent_ids:
            agent_query["_id"] = {"$in": [parse_object_id(agent_id, "agent") for agent_id in request.agent_ids]}
        elif request.respect_availability:
            agent_query["available"] = True

        candidate_orders = [serialize_order(order) for order in orders.find(order_query).sort("created_at", 1)]
        candidate_agents = []
        for agent in agents.find(agent_query).sort("created_at", 1):
            agent_payload = {
                "id": str(agent["_id"]),
                "name": agent["name"],
                "lat": agent["lat"],
                "lng": agent["lng"],
                "available": agent.get("available", True),
                "current_load": agent.get("current_load", 0),
                "active_order_ids": agent.get("active_order_ids", []),
            }
            candidate_agents.append(agent_payload)

        if not candidate_orders:
            return {"assignments": {}, "message": "No matching orders to assign"}
        if not candidate_agents:
            return {"assignments": {}, "message": "No matching agents available"}

        assignments = assign_orders(candidate_orders, candidate_agents)

        # Update orders with assignments
        for agent_id, order_ids in assignments.items():
            parsed_agent_id = parse_object_id(agent_id, "agent")
            agent = agents.find_one({"_id": parsed_agent_id})
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found during assignment")

            for order_id in order_ids:
                parsed_order_id = parse_object_id(order_id, "order")
                current_order = orders.find_one({"_id": parsed_order_id})
                if not current_order:
                    raise HTTPException(status_code=404, detail=f"Order {order_id} not found during assignment")
                if current_order.get("status") != "placed":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Order {order_id} is not eligible for assignment",
                    )
                if current_order.get("fulfillment_mode", "delivery") != "delivery":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Order {order_id} is a takeaway order and cannot be assigned",
                    )

                orders.update_one(
                    {"_id": parsed_order_id},
                    {
                        "$set": {
                            "assigned_agent_id": agent_id,
                            "assigned_agent_name": agent["name"] if agent else None,
                            "assignment_status": "assigned",
                            "status": "accepted" if request.auto_update_status else "placed",
                            "prep_status": "preparing" if request.auto_update_status else "queued",
                            "updated_at": datetime.utcnow(),
                        }
                    }
                )

            sync_agent_load(agent_id)

        return {
            "assignments": assignments,
            "message": "Orders assigned successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/agent/{agent_id}")
def get_agent_orders(agent_id: str):
    """Get all orders assigned to a specific agent"""
    try:
        agent_orders = list(orders.find({"assigned_agent_id": agent_id}).sort("created_at", -1))
        result = [serialize_order(order) for order in agent_orders]
        return {"agent_id": agent_id, "orders": result, "count": len(result)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
