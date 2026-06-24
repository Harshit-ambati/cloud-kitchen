"""
Database Index Management
--------------------------
Creates indexes required for query performance and data integrity.
Called once at application startup.

Updated to include:
    - branches collection indexes
    - user role + branch_id compound index
    - user is_active index
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
        # ── Orders ────────────────────────────────────────────────────
        orders = db["orders"]
        orders.create_index([("branch_id", ASCENDING)], background=True)
        orders.create_index([("assigned_agent_id", ASCENDING)], background=True)
        orders.create_index([("is_simulated", ASCENDING)], background=True)
        orders.create_index([("status", ASCENDING)], background=True)
        orders.create_index(
            [("branch_id", ASCENDING), ("status", ASCENDING)],
            background=True,
        )
        orders.create_index([("customer_user_id", ASCENDING)], background=True)

        # ── Agents ────────────────────────────────────────────────────
        agents = db["agents"]
        agents.create_index([("branch_id", ASCENDING)], background=True)
        agents.create_index([("user_id", ASCENDING)], background=True)

        # ── Users ─────────────────────────────────────────────────────
        users = db["users"]
        users.create_index([("email", ASCENDING)], unique=True, background=True)
        users.create_index([("phone", ASCENDING)], background=True)
        users.create_index([("role", ASCENDING)], background=True)
        users.create_index(
            [("role", ASCENDING), ("branch_id", ASCENDING)],
            background=True,
        )
        users.create_index([("is_active", ASCENDING)], background=True)

        # ── Branches ──────────────────────────────────────────────────
        branches = db["branches"]
        branches.create_index([("id", ASCENDING)], unique=True, background=True)
        branches.create_index([("status", ASCENDING)], background=True)
        branches.create_index([("is_active", ASCENDING)], background=True)

        # OTP login
        otps = db["otp_codes"]
        otps.create_index([("phone", ASCENDING)], background=True)
        otps.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)

        logger.info("INDEXES | All indexes ensured successfully")
    except PyMongoError as exc:
        # Non-fatal — the app can still function without indexes,
        # just with slower queries.
        logger.warning("INDEXES | Failed to create indexes: %s", exc)
