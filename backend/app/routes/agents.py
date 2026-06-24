import logging
from datetime import datetime

from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.dependencies.auth import CurrentUser, build_agent_filter, build_order_filter, get_current_user, log_access
from app.db import agents, orders
from app.models import AgentCreate, AgentUpdate
from app.services.policy import enforce_not_delivery, enforce_ownership, filter_agent_update
from app.services.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()


def serialize_agent(agent):
    return {
        "id": str(agent["_id"]),
        "name": agent["name"],
        "lat": agent["lat"],
        "lng": agent["lng"],
        "available": agent.get("available", True),
        "status": "available" if agent.get("available", True) else "busy",
        "current_load": agent.get("current_load", 0),
        "active_order_ids": agent.get("active_order_ids", []),
        "total_deliveries": agent.get("total_deliveries", 0),
        "avg_rating": agent.get("avg_rating", 5.0),
        "branch_id": agent.get("branch_id"),
        "created_at": agent.get("created_at"),
        "updated_at": agent.get("updated_at"),
    }


def parse_object_id(value, resource_name):
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {resource_name} id") from exc


@router.post("/create")
def create_agent(agent: AgentCreate, current_user: CurrentUser = Depends(get_current_user)):
    """Create a new delivery agent (admin/manager only)"""
    enforce_not_delivery(current_user, "create agents")

    try:
        agent_data = agent.dict()
        if current_user.is_branch_manager:
            agent_data["branch_id"] = current_user.branch_id
        agent_data["created_at"] = datetime.utcnow()
        agent_data["updated_at"] = agent_data["created_at"]
        agent_data["total_deliveries"] = 0
        agent_data["avg_rating"] = 5.0
        agent_data["current_load"] = 0
        agent_data["active_order_ids"] = []

        result = agents.insert_one(agent_data)
        created_agent = agents.find_one({"_id": result.inserted_id})
        return serialize_agent(created_agent)
    except PyMongoError as exc:
        logger.error("DB_ERROR | create_agent failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.get("/")
def get_all_agents(current_user: CurrentUser = Depends(get_current_user)):
    """Get all delivery agents (filtered by role)"""
    query = build_agent_filter(current_user)
    try:
        all_agents = [serialize_agent(agent) for agent in agents.find(query).sort("created_at", -1)]
    except PyMongoError as exc:
        logger.warning("DB_WARN | agents/list unavailable: %s", exc)
        return error_response("Database unavailable", agents=[])

    log_access(current_user, "agents/list", len(all_agents))
    return success_response(agents=all_agents)


@router.get("/{agent_id}")
def get_agent(agent_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get a specific agent by ID (enforces role-based access)"""
    try:
        agent = agents.find_one(
            build_agent_filter(current_user, {"_id": parse_object_id(agent_id, "agent")})
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or access denied")

        log_access(current_user, f"agents/{agent_id}", 1)
        return serialize_agent(agent)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | get_agent failed for %s: %s", agent_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{agent_id}")
def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Update agent location and availability.
    Delivery/agent users can only update their own profile,
    and only lat/lng/available fields.
    """
    # Policy: agents can only update themselves
    if current_user.is_delivery_agent:
        enforce_ownership(current_user, agent_id)

    try:
        update_data = {
            key: value
            for key, value in agent_update.dict().items()
            if value is not None
        }

        # Policy: strip restricted fields for delivery/agent users
        update_data = filter_agent_update(current_user, update_data)

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_data["updated_at"] = datetime.utcnow()

        scoped_agent_query = build_agent_filter(current_user, {"_id": parse_object_id(agent_id, "agent")})
        result = agents.update_one(scoped_agent_query, {"$set": update_data})

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Agent not found or access denied")

        updated_agent = agents.find_one(scoped_agent_query)
        return serialize_agent(updated_agent)
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | update_agent failed for %s: %s", agent_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{agent_id}")
def delete_agent(agent_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete an agent (admin/manager only)"""
    enforce_not_delivery(current_user, "delete agents")

    try:
        parsed_agent_id = parse_object_id(agent_id, "agent")
        scoped_agent_query = build_agent_filter(current_user, {"_id": parsed_agent_id})
        if not agents.find_one(scoped_agent_query):
            raise HTTPException(status_code=404, detail="Agent not found or access denied")

        active_orders = orders.count_documents(
            build_order_filter(
                current_user,
                {
                    "$or": [
                        {"assigned_delivery_id": agent_id},
                        {"assigned_agent_id": agent_id},
                    ],
                    "status": {"$in": ["accepted", "in_transit"]},
                },
            )
        )
        if active_orders:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete agent with active assigned orders",
            )

        result = agents.delete_one(scoped_agent_query)

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Agent not found")

        return success_response(message="Agent deleted successfully")
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | delete_agent failed for %s: %s", agent_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
