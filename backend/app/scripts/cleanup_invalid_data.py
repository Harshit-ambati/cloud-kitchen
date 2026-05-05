import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db import orders, agents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scan_invalid_documents():
    logger.info("Scanning database for invalid orders...")
    
    invalid_orders = []
    for order in orders.find({}):
        lat = order.get("user_lat")
        lng = order.get("user_lng")
        
        if lat is None or lng is None:
            invalid_orders.append((order["_id"], "Missing lat/lng"))
            continue
            
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            invalid_orders.append((order["_id"], f"Invalid types: lat={type(lat)}, lng={type(lng)}"))
            continue
            
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            invalid_orders.append((order["_id"], f"Out of bounds: {lat}, {lng}"))

    if invalid_orders:
        logger.warning(f"Found {len(invalid_orders)} invalid orders.")
        for oid, reason in invalid_orders:
            logger.warning(f"  - Order {oid}: {reason}")
    else:
        logger.info("All orders are valid.")

    logger.info("Scanning database for invalid agents...")
    invalid_agents = []
    for agent in agents.find({}):
        lat = agent.get("lat")
        lng = agent.get("lng")
        
        if lat is None or lng is None:
            invalid_agents.append((agent["_id"], "Missing lat/lng"))
            continue
            
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            invalid_agents.append((agent["_id"], f"Invalid types: lat={type(lat)}, lng={type(lng)}"))
            continue
            
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            invalid_agents.append((agent["_id"], f"Out of bounds: {lat}, {lng}"))
            
    if invalid_agents:
        logger.warning(f"Found {len(invalid_agents)} invalid agents.")
        for aid, reason in invalid_agents:
            logger.warning(f"  - Agent {aid}: {reason}")
    else:
        logger.info("All agents are valid.")

if __name__ == "__main__":
    scan_invalid_documents()
