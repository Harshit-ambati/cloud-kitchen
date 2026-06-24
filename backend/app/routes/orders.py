import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import PyMongoError

from app.dependencies.auth import CurrentUser, build_agent_filter, build_order_filter, get_current_user, log_access

from app.db import agents, orders
from app.models import AssignmentRequest, OrderCreate, OrderStatusUpdate
from app.services.distance import haversine
from app.services.optimizer import assign_orders
from app.services.branch_selector import assign_branch, is_within_delivery_range
from app.services.branch_config import get_service_radius
from app.services.metrics import estimate_delivery_time
from app.services.policy import enforce_not_delivery, enforce_delivery_status_permission
from app.services.response import success_response, error_response, partial_response
from app.services.sanitizer import sanitize_orders_for_optimizer, sanitize_agents_for_optimizer
from ml.predict_eta import predict_eta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
        "assigned_batch_id": order.get("assigned_batch_id"),
        "assigned_batch_size": order.get("assigned_batch_size", 1),
        "route_stop_number": order.get("route_stop_number"),
        "batch_stop_number": order.get("batch_stop_number"),
        "batch_order_ids": order.get("batch_order_ids", []),
        "distance_km": round(order.get("distance_km", 0), 2),
        "predicted_prep_minutes": order.get("predicted_prep_minutes", 0),
        "predicted_travel_minutes": order.get("predicted_travel_minutes", 0),
        "predicted_eta_minutes": order.get("predicted_eta_minutes", 0),
        "estimated_delivery_at": order.get("estimated_delivery_at"),
        "pickup_ready_at": order.get("pickup_ready_at"),
        "is_simulated": order.get("is_simulated", False),
        "branch_id": order.get("branch_id"),
        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at"),
    }


def parse_object_id(value, resource_name):
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {resource_name} id") from exc


def sanitize_orders(orders_cursor):
    valid_orders = []
    invalid_count = 0
    for order in orders_cursor:
        lat = order.get("user_lat")
        lng = order.get("user_lng")
        if lat is None or lng is None or not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            invalid_count += 1
            logger.warning(f"Skipped invalid order {order.get('_id')}: Bad lat/lng")
            continue
        valid_orders.append(serialize_order(order))
    return valid_orders, invalid_count


def get_allowed_status_transitions(order):
    if order.get("fulfillment_mode", "delivery") == "takeaway":
        return TAKEAWAY_STATUS_TRANSITIONS
    return DELIVERY_STATUS_TRANSITIONS


def _build_type_filter(order_type: Optional[str]) -> dict:
    """
    Build a MongoDB filter clause for the ?type= query parameter.
    Returns an empty dict for 'all' (no filter), which is the default.
    """
    if order_type == "real":
        return {"$or": [{"is_simulated": False}, {"is_simulated": {"$exists": False}}]}
    elif order_type == "simulated":
        return {"is_simulated": True}
    return {}  # "all" — no filter


def sync_agent_load(agent_id):
    """Sync agent load from DB. Non-critical — failures are logged and swallowed."""
    try:
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
    except PyMongoError as exc:
        logger.warning("DB_WARN | sync_agent_load failed for agent %s: %s", agent_id, exc)


def increment_agent_delivery_stats(agent_id):
    """Increment delivery counter. Non-critical — failures are logged and swallowed."""
    try:
        agents.update_one(
            {"_id": ObjectId(agent_id)},
            {
                "$inc": {"total_deliveries": 1},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
    except PyMongoError as exc:
        logger.warning("DB_WARN | increment_agent_delivery_stats failed for agent %s: %s", agent_id, exc)


def calculate_route_eta_updates(route_batches, order_lookup, eta_origin_time):
    eta_updates = {}
    cumulative_travel_minutes = 0
    prep_ready_ceiling = 0
    current_location = None

    for route_batch in route_batches:
        batch_orders = [order_lookup[order_id] for order_id in route_batch["order_ids"] if order_id in order_lookup]
        if not batch_orders:
            continue

        prep_ready_ceiling = max(
            prep_ready_ceiling,
            max(order.get("predicted_prep_minutes", 0) for order in batch_orders),
        )

        for order in batch_orders:
            if current_location is None:
                current_location = (order["kitchen_lat"], order["kitchen_lng"])

            segment_distance = haversine(
                current_location[0],
                current_location[1],
                order["user_lat"],
                order["user_lng"],
            )
            segment_travel_minutes = predict_eta(segment_distance)
            cumulative_travel_minutes = round(cumulative_travel_minutes + segment_travel_minutes, 2)
            route_eta_minutes = round(prep_ready_ceiling + cumulative_travel_minutes, 2)

            eta_updates[order["id"]] = {
                "predicted_travel_minutes": cumulative_travel_minutes,
                "predicted_eta_minutes": route_eta_minutes,
                "estimated_delivery_at": eta_origin_time + timedelta(minutes=route_eta_minutes),
            }
            current_location = (order["user_lat"], order["user_lng"])

    return eta_updates


# ═══════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════

@router.post("/create")
def create_order(
    order: OrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    debug: bool = Query(False, description="Include branch selection trace"),
):
    """Create a new order with ETA calculation"""
    try:
        data = order.dict()
        data["customer_user_id"] = current_user.user_id
        if current_user.is_customer:
            data["customer_phone"] = data.get("customer_phone") or ""
            data["customer_name"] = data.get("customer_name") or current_user.name or "Customer"

        if data.get("user_lat") is None or data.get("user_lng") is None:
            raise HTTPException(status_code=400, detail="Missing user_lat or user_lng")

        items = data.get("items", [])
        fulfillment_mode = data.get("fulfillment_mode", "delivery")

        # Dynamic nearest-branch assignment (with optional decision trace)
        if debug:
            selected_branch, distance_to_branch, branch_trace = assign_branch(
                data["user_lat"], data["user_lng"], debug=True,
            )
        else:
            selected_branch, distance_to_branch = assign_branch(
                data["user_lat"], data["user_lng"],
            )
            branch_trace = None

        # Per-branch radius check
        if fulfillment_mode == "delivery" and not is_within_delivery_range(
            distance_to_branch, branch_id=selected_branch["id"]
        ):
            radius = get_service_radius(selected_branch["id"])
            raise HTTPException(
                status_code=400,
                detail=(
                    "Delivery address is outside our service range. "
                    f"Nearest branch is {distance_to_branch:.2f} km away; "
                    f"maximum supported distance is {radius} km."
                ),
            )

        logger.info(json.dumps({
            "user_location": (data["user_lat"], data["user_lng"]),
            "assigned_branch": selected_branch["name"],
            "distance_km": round(distance_to_branch, 2)
        }))

        # Override kitchen lat/lng to route without changing schema
        data["kitchen_lat"] = selected_branch["lat"]
        data["kitchen_lng"] = selected_branch["lng"]
        data["branch_id"] = selected_branch["id"]

        distance = haversine(
            data["user_lat"], data["user_lng"],
            data["kitchen_lat"], data["kitchen_lng"]
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
        data["estimated_delivery_time"] = estimate_delivery_time(distance)
        data["predicted_travel_minutes"] = travel_eta
        data["predicted_prep_minutes"] = prep_eta
        data["predicted_eta_minutes"] = round(prep_eta + travel_eta, 2)
        data["status"] = "placed"
        data["prep_status"] = "queued"
        data["assignment_status"] = "unassigned"
        data["assigned_agent_id"] = None
        data["assigned_delivery_id"] = None
        data["assigned_agent_name"] = None
        data["assigned_batch_id"] = None
        data["assigned_batch_size"] = 1
        data["route_stop_number"] = None
        data["batch_stop_number"] = None
        data["batch_order_ids"] = []
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = data["created_at"]
        data["estimated_delivery_at"] = (
            data["created_at"] + timedelta(minutes=data["predicted_eta_minutes"])
            if fulfillment_mode == "delivery"
            else None
        )
        data["pickup_ready_at"] = (
            data["created_at"] + timedelta(minutes=prep_eta) if fulfillment_mode == "takeaway" else None
        )

        result = orders.insert_one(data)
        created_order = orders.find_one({"_id": result.inserted_id})
        response = serialize_order(created_order)

        if branch_trace:
            response["_debug"] = {"branch_selection": branch_trace}

        return response
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | create_order failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def get_all_orders(
    current_user: CurrentUser = Depends(get_current_user),
    type: Optional[str] = Query(None, pattern="^(real|simulated|all)$", description="Filter: real, simulated, or all"),
):
    """Get all orders (filtered by role + optional type filter)"""
    type_filter = _build_type_filter(type)
    query = build_order_filter(current_user, type_filter if type_filter else None)
    try:
        orders_cursor = orders.find(query).sort("created_at", -1)
        valid_orders, invalid_count = sanitize_orders(orders_cursor)
    except PyMongoError as exc:
        logger.warning("orders/list unavailable because MongoDB is unreachable: %s", exc)
        return error_response("Database unavailable", orders=[], count=0)

    log_access(current_user, "orders/list", len(valid_orders))
    return success_response(
        orders=valid_orders,
        count=len(valid_orders),
        invalid_orders_skipped=invalid_count,
    )


@router.get("/agent/{agent_id}")
def get_agent_orders(agent_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get all orders assigned to a specific agent (filtered by role)"""
    try:
        # Delivery users can only see their own orders
        if current_user.is_delivery_agent and agent_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Access denied: you can only view your own orders")

        query = build_order_filter(
            current_user,
            {
                "$or": [
                    {"assigned_delivery_id": agent_id},
                    {"assigned_agent_id": agent_id},
                ]
            },
        )
        agent_orders_cursor = orders.find(query).sort("created_at", -1)
        valid_orders, invalid_count = sanitize_orders(agent_orders_cursor)
        log_access(current_user, f"orders/agent/{agent_id}", len(valid_orders))
        return success_response(
            agent_id=agent_id,
            orders=valid_orders,
            count=len(valid_orders),
            invalid_orders_skipped=invalid_count,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.warning("DB_WARN | get_agent_orders failed: %s", exc)
        return error_response("Database unavailable", agent_id=agent_id, orders=[], count=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}")
def get_order(order_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get a specific order by ID (enforces role-based access)"""
    try:
        order = orders.find_one(
            build_order_filter(current_user, {"_id": parse_object_id(order_id, "order")})
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found or access denied")

        log_access(current_user, f"orders/{order_id}", 1)
        return serialize_order(order)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | get_order failed for %s: %s", order_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{order_id}/status")
def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update order status (delivery users restricted to in_transit/delivered)"""
    status = status_update.status

    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")

    # Policy: delivery/agent users can only set delivery-related statuses
    enforce_delivery_status_permission(current_user, status)

    try:
        parsed_order_id = parse_object_id(order_id, "order")
        scoped_order_query = build_order_filter(current_user, {"_id": parsed_order_id})
        existing_order = orders.find_one(scoped_order_query)
        if not existing_order:
            raise HTTPException(status_code=404, detail="Order not found or access denied")

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
            scoped_order_query,
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
            raise HTTPException(status_code=404, detail="Order not found or access denied")

        updated_order = orders.find_one(scoped_order_query)
        if updated_order.get("assigned_agent_id"):
            if status == "delivered" and current_status != "delivered":
                increment_agent_delivery_stats(updated_order["assigned_agent_id"])
            sync_agent_load(updated_order["assigned_agent_id"])

        return serialize_order(updated_order)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | update_order_status failed for %s: %s", order_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimize-assignments")
def optimize_assignments(
    request: Optional[AssignmentRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    debug: bool = Query(False, description="Include optimizer debug trace"),
):
    """Optimize and assign orders to agents (admin/manager only)"""
    enforce_not_delivery(current_user, "run assignment optimization")

    try:
        request = request or AssignmentRequest()
        order_query = build_order_filter(current_user, {"status": "placed", "fulfillment_mode": "delivery"})
        if request.order_ids:
            order_query = build_order_filter(current_user, {
                "_id": {"$in": [parse_object_id(order_id, "order") for order_id in request.order_ids]},
                "status": "placed",
                "fulfillment_mode": "delivery",
            })

        agent_query = {}
        if request.agent_ids:
            agent_query["_id"] = {"$in": [parse_object_id(agent_id, "agent") for agent_id in request.agent_ids]}
        elif request.respect_availability:
            agent_query["available"] = True
        agent_query = build_agent_filter(current_user, agent_query)

        raw_candidate_orders = orders.find(order_query).sort("created_at", 1)
        candidate_orders, invalid_orders_skipped = sanitize_orders(raw_candidate_orders)

        # Build raw agent list
        raw_candidate_agents = []
        for agent in agents.find(agent_query).sort("created_at", 1):
            if agent.get("lat") is None or agent.get("lng") is None:
                continue
            raw_candidate_agents.append({
                "id": str(agent["_id"]),
                "name": agent["name"],
                "lat": agent["lat"],
                "lng": agent["lng"],
                "available": agent.get("available", True),
                "current_load": agent.get("current_load", 0),
                "active_order_ids": agent.get("active_order_ids", []),
            })

        # Sanitize through DTO layer before optimizer
        validated_orders, orders_dropped_by_sanitizer = sanitize_orders_for_optimizer(candidate_orders)
        validated_agents, agents_dropped_by_sanitizer = sanitize_agents_for_optimizer(raw_candidate_agents)

        sanitizer_meta = {
            "orders_dropped_by_sanitizer": orders_dropped_by_sanitizer,
            "agents_dropped_by_sanitizer": agents_dropped_by_sanitizer,
        } if debug else {}

        if not validated_orders:
            return partial_response(
                "No valid matching orders to assign",
                assignments={},
                invalid_orders_skipped=invalid_orders_skipped,
                **sanitizer_meta,
            )
        if not validated_agents:
            return partial_response(
                "No valid matching agents available",
                assignments={},
                invalid_orders_skipped=invalid_orders_skipped,
                **sanitizer_meta,
            )

        try:
            assignments = assign_orders(validated_orders, validated_agents)
        except Exception as e:
            logger.error(f"Route optimizer crashed: {e}", exc_info=True)
            return partial_response(
                "Route optimizer encountered an error. Safely returning empty assignments.",
                assignments={},
                invalid_orders_skipped=invalid_orders_skipped,
            )

        candidate_order_lookup = {order["id"]: order for order in candidate_orders}
        assignment_started_at = datetime.utcnow()

        # Update orders with assignments
        for agent_id, route_batches in assignments.items():
            parsed_agent_id = parse_object_id(agent_id, "agent")
            agent = agents.find_one({"_id": parsed_agent_id})
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found during assignment")

            route_eta_updates = calculate_route_eta_updates(route_batches, candidate_order_lookup, assignment_started_at)
            route_stop_number = 1

            for route_batch in route_batches:
                order_ids = route_batch["order_ids"]
                batch_id = route_batch.get("batch_id")
                batch_size = route_batch.get("batch_size", len(order_ids))

                for batch_stop_number, order_id in enumerate(order_ids, start=1):
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

                    eta_update = route_eta_updates.get(
                        order_id,
                        {
                            "predicted_travel_minutes": current_order.get("predicted_travel_minutes", 0),
                            "predicted_eta_minutes": current_order.get("predicted_eta_minutes", 0),
                            "estimated_delivery_at": current_order.get("estimated_delivery_at"),
                        },
                    )

                    orders.update_one(
                        {"_id": parsed_order_id},
                        {
                            "$set": {
                                "assigned_agent_id": agent_id,
                                "assigned_delivery_id": agent_id,
                                "assigned_agent_name": agent["name"] if agent else None,
                                "assignment_status": "assigned",
                                "assigned_batch_id": batch_id,
                                "assigned_batch_size": batch_size,
                                "route_stop_number": route_stop_number,
                                "batch_stop_number": batch_stop_number,
                                "batch_order_ids": order_ids if batch_size > 1 else [],
                                "predicted_travel_minutes": eta_update["predicted_travel_minutes"],
                                "predicted_eta_minutes": eta_update["predicted_eta_minutes"],
                                "estimated_delivery_at": eta_update["estimated_delivery_at"],
                                "status": "accepted" if request.auto_update_status else "placed",
                                "prep_status": "preparing" if request.auto_update_status else "queued",
                                "updated_at": assignment_started_at,
                            }
                        }
                    )
                    route_stop_number += 1

            sync_agent_load(agent_id)

        return success_response(
            assignments=assignments,
            message="Orders assigned successfully",
            invalid_orders_skipped=invalid_orders_skipped,
            **sanitizer_meta,
        )
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | optimize_assignments failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
