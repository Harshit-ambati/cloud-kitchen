"""
Branch Selection Service
--------------------------
Assigns the optimal kitchen branch based on distance, current load,
and per-branch service radius configuration.

Resilient: if MongoDB is down, load data comes from cache or
defaults to zero (pure nearest-branch routing).
"""

import logging
from typing import Optional

from app.db import orders
from app.services.branches import BRANCHES
from app.services.branch_config import get_service_radius, DEFAULT_SERVICE_RADIUS_KM
from app.services.cache import cache
from app.services.distance import haversine

logger = logging.getLogger(__name__)

# Cache key for branch load counts
_BRANCH_LOADS_CACHE_KEY = "branch_loads"
_BRANCH_LOADS_TTL = 60  # refresh every 60 seconds

LOAD_WEIGHT = 0.5  # 1 active order adds 0.5 km equivalent penalty


def _get_branch_loads() -> dict:
    """
    Fetch active-order counts per branch from MongoDB.
    On DB failure, fall back to the in-memory cache.
    If no cache exists either, return zeros (pure distance routing).
    """
    active_statuses = ["placed", "accepted", "in_transit", "ready_for_pickup", "preparing"]

    try:
        pipeline = [
            {"$match": {"status": {"$in": active_statuses}}},
            {"$group": {"_id": "$branch_id", "count": {"$sum": 1}}},
        ]
        loads = {row["_id"]: row["count"] for row in orders.aggregate(pipeline)}

        # Warm the cache on every successful fetch
        cache.set(_BRANCH_LOADS_CACHE_KEY, loads, ttl=_BRANCH_LOADS_TTL)
        return loads

    except Exception as exc:
        logger.warning("DB unavailable for branch loads, attempting cache fallback: %s", exc)
        cached = cache.get(_BRANCH_LOADS_CACHE_KEY)
        if cached is not None:
            logger.info("CACHE_HIT | Serving branch loads from cache")
            return cached

        logger.warning("CACHE_MISS | No cached branch loads available, defaulting to zero loads")
        return {}


def assign_branch(
    user_lat: float,
    user_lng: float,
    debug: bool = False,
) -> tuple:
    """
    Assigns the optimal branch based on distance and current load.

    Returns:
        (selected_branch_dict, distance_km)              when debug=False
        (selected_branch_dict, distance_km, trace_info)   when debug=True
    """
    best_branch = None
    min_score = float('inf')

    nearest_branch = None
    min_distance = float('inf')

    # Get loads — this call is resilient (DB → cache → zero)
    branch_loads = _get_branch_loads()

    # Decision trace (populated only when debug=True)
    candidates = []

    for branch in BRANCHES:
        distance = haversine(user_lat, user_lng, branch['lat'], branch['lng'])
        radius = get_service_radius(branch["id"])
        active_orders_count = branch_loads.get(branch["id"], 0)
        score = distance + (active_orders_count * LOAD_WEIGHT)

        if debug:
            candidates.append({
                "branch_id": branch["id"],
                "branch_name": branch["name"],
                "distance_km": round(distance, 2),
                "service_radius_km": radius,
                "active_orders": active_orders_count,
                "load_penalty": round(active_orders_count * LOAD_WEIGHT, 2),
                "score": round(score, 2),
                "within_radius": distance <= radius,
            })

        # Track the strictly nearest branch for fallback
        if distance < min_distance:
            min_distance = distance
            nearest_branch = branch

        if score < min_score:
            min_score = score
            best_branch = branch

    # Fallback: if all branches are further than 10km, assign nearest
    if min_distance > 10:
        selected = nearest_branch
        reason = "nearest_fallback_all_branches_far"
    else:
        selected = best_branch
        reason = "min_load_within_radius"

    final_distance = haversine(user_lat, user_lng, selected['lat'], selected['lng'])

    if debug:
        trace = {
            "selected_branch": selected["id"],
            "selected_branch_name": selected["name"],
            "reason": reason,
            "distance_km": round(final_distance, 2),
            "candidates_checked": len(candidates),
            "candidates": candidates,
        }
        return selected, final_distance, trace

    return selected, final_distance


def is_within_delivery_range(distance_km: float, branch_id: Optional[str] = None) -> bool:
    """
    Check if a distance is within the delivery range.
    Uses per-branch radius if branch_id is provided, otherwise default.
    """
    if branch_id:
        radius = get_service_radius(branch_id)
    else:
        radius = DEFAULT_SERVICE_RADIUS_KM
    return distance_km <= radius
