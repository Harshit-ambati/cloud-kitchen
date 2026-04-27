from datetime import datetime

from bson.objectid import ObjectId
from fastapi import APIRouter, HTTPException

from app.db import agents, orders
from app.models import AgentCreate, AgentUpdate

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
        "created_at": agent.get("created_at"),
        "updated_at": agent.get("updated_at"),
    }


def parse_object_id(value, resource_name):
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {resource_name} id") from exc


@router.post("/create")
def create_agent(agent: AgentCreate):
    """Create a new delivery agent"""
    agent_data = agent.dict()
    agent_data["created_at"] = datetime.utcnow()
    agent_data["updated_at"] = agent_data["created_at"]
    agent_data["total_deliveries"] = 0
    agent_data["avg_rating"] = 5.0
    agent_data["current_load"] = 0
    agent_data["active_order_ids"] = []

    result = agents.insert_one(agent_data)
    created_agent = agents.find_one({"_id": result.inserted_id})
    return serialize_agent(created_agent)

@router.get("/")
def get_all_agents():
    """Get all delivery agents"""
    all_agents = [serialize_agent(agent) for agent in agents.find().sort("created_at", -1)]
    return {"agents": all_agents}

@router.get("/{agent_id}")
def get_agent(agent_id: str):
    """Get a specific agent by ID"""
    try:
        agent = agents.find_one({"_id": parse_object_id(agent_id, "agent")})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return serialize_agent(agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{agent_id}")
def update_agent(agent_id: str, agent_update: AgentUpdate):
    """Update agent location and availability"""
    try:
        update_data = {
            key: value
            for key, value in agent_update.dict().items()
            if value is not None
        }
        update_data["updated_at"] = datetime.utcnow()

        result = agents.update_one(
            {"_id": parse_object_id(agent_id, "agent")},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Agent not found")

        updated_agent = agents.find_one({"_id": parse_object_id(agent_id, "agent")})
        return serialize_agent(updated_agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{agent_id}")
def delete_agent(agent_id: str):
    """Delete an agent"""
    try:
        parsed_agent_id = parse_object_id(agent_id, "agent")
        active_orders = orders.count_documents(
            {
                "assigned_agent_id": agent_id,
                "status": {"$in": ["accepted", "in_transit"]},
            }
        )
        if active_orders:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete agent with active assigned orders",
            )

        result = agents.delete_one({"_id": parsed_agent_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {"message": "Agent deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
