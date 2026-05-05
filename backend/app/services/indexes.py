"""
Database Index Management
--------------------------
Creates indexes required for query performance and data integrity.
Called once at application startup.
"""

import logging
from pymongo.errors import PyMongoError
from pymongo import ASCENDING

from app.db import db

logger = logging.getLogger(__name__)


def ensure_indexes() -> None:
    """
    Create MongoDB indexes idempotently (create_index is a no-op
    if the index already exists with the same spec).
    """
    try:
        orders = db["orders"]
        orders.create_index([("branch_id", ASCENDING)], background=True)
        orders.create_index([("assigned_agent_id", ASCENDING)], background=True)
        orders.create_index([("is_simulated", ASCENDING)], background=True)
        orders.create_index([("status", ASCENDING)], background=True)
        orders.create_index(
            [("branch_id", ASCENDING), ("status", ASCENDING)],
            background=True,
        )

        agents = db["agents"]
        agents.create_index([("branch_id", ASCENDING)], background=True)

        users = db["users"]
        users.create_index([("email", ASCENDING)], unique=True, background=True)

        logger.info("INDEXES | All indexes ensured successfully")
    except PyMongoError as exc:
        # Non-fatal — the app can still function without indexes,
        # just with slower queries.
        logger.warning("INDEXES | Failed to create indexes: %s", exc)
