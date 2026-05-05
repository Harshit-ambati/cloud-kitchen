"""
Health Check & Readiness Endpoint
-----------------------------------
GET /health — returns database connectivity status and cache stats.
"""

import logging

from fastapi import APIRouter
from pymongo.errors import PyMongoError

from app.db import client
from app.services.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    """
    Lightweight probe for load balancers and monitoring.
    Always returns 200 so the frontend never sees a hard failure
    on this route — the ``db_connected`` field reveals the truth.
    """
    db_connected = False
    db_latency_ms = None

    try:
        # ping is the cheapest possible round-trip to MongoDB
        info = client.admin.command("ping")
        db_connected = info.get("ok") == 1.0
        db_latency_ms = "< 5000"  # if we got here within the socket timeout
    except PyMongoError as exc:
        logger.warning("Health check: MongoDB unreachable — %s", exc)
    except Exception as exc:
        logger.error("Health check unexpected error — %s", exc)

    return {
        "status": "ok" if db_connected else "degraded",
        "db_connected": db_connected,
        "db_latency": db_latency_ms,
        "cache": cache.info(),
    }
