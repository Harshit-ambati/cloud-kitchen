"""
Metrics & Performance Tracking Service
---------------------------------------
Internal-only analytics for comparing multi-branch vs single-kitchen efficiency.
Nothing in this module is exposed to the frontend.
"""

import logging
from pymongo.errors import PyMongoError

from app.db import orders
from app.services.distance import haversine
from app.services.branches import BRANCHES

logger = logging.getLogger(__name__)

# ── Delivery-time estimation constants ──────────────────────────────────────
BASE_DELIVERY_TIME_MIN = 10   # fixed overhead: pickup, packaging, handoff
TIME_PER_KM_MIN = 3           # minutes added for every kilometre of distance

# ── Central kitchen location (legacy single-kitchen reference point) ────────
CENTRAL_KITCHEN = {"lat": 17.385, "lng": 78.4867}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Point-to-point helpers
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_distance(user_lat: float, user_lng: float,
                       kitchen_lat: float, kitchen_lng: float) -> float:
    """Haversine wrapper — returns distance in km (rounded to 2 dp)."""
    return round(haversine(user_lat, user_lng, kitchen_lat, kitchen_lng), 2)


def estimate_delivery_time(distance_km: float) -> float:
    """
    Simple linear model:
        time = base_time + (distance_km × factor)
    Returns estimated minutes (rounded to 2 dp).
    """
    return round(BASE_DELIVERY_TIME_MIN + (distance_km * TIME_PER_KM_MIN), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Aggregation summary
# ═══════════════════════════════════════════════════════════════════════════════

def get_metrics_summary() -> dict:
    """
    Aggregate metrics across all orders stored in MongoDB.

    Returns:
        {
            total_orders,
            average_distance,
            average_delivery_time,
            orders_per_branch
        }
    """
    pipeline_stats = [
        {
            "$group": {
                "_id": None,
                "total_orders": {"$sum": 1},
                "avg_distance": {"$avg": "$distance_km"},
                "avg_delivery_time": {"$avg": "$estimated_delivery_time"},
            }
        }
    ]

    pipeline_branch = [
        {
            "$group": {
                "_id": "$branch_id",
                "count": {"$sum": 1},
                "avg_distance": {"$avg": "$distance_km"},
                "avg_delivery_time": {"$avg": "$estimated_delivery_time"},
            }
        },
        {"$sort": {"count": -1}},
    ]

    try:
        stats_result = list(orders.aggregate(pipeline_stats))
        branch_result = list(orders.aggregate(pipeline_branch))
    except PyMongoError as exc:
        logger.error("DB_ERROR | get_metrics_summary aggregation failed: %s", exc)
        return {
            "total_orders": 0,
            "average_distance": 0,
            "average_delivery_time": 0,
            "orders_per_branch": {},
        }

    if not stats_result:
        return {
            "total_orders": 0,
            "average_distance": 0,
            "average_delivery_time": 0,
            "orders_per_branch": {},
        }

    stats = stats_result[0]

    orders_per_branch = {}
    for row in branch_result:
        branch_id = row["_id"] or "unknown"
        # Look up the human-readable branch name
        branch_name = next(
            (b["name"] for b in BRANCHES if b["id"] == branch_id),
            branch_id,
        )
        orders_per_branch[branch_id] = {
            "name": branch_name,
            "count": row["count"],
            "avg_distance_km": round(row.get("avg_distance") or 0, 2),
            "avg_delivery_time_min": round(row.get("avg_delivery_time") or 0, 2),
        }

    return {
        "total_orders": stats["total_orders"],
        "average_distance": round(stats.get("avg_distance") or 0, 2),
        "average_delivery_time": round(stats.get("avg_delivery_time") or 0, 2),
        "orders_per_branch": orders_per_branch,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Single-kitchen vs Multi-branch comparison
# ═══════════════════════════════════════════════════════════════════════════════

def get_comparison_metrics() -> dict:
    """
    For every order in the database, compute what the distance *would have been*
    if served from the single central kitchen, then compare with the actual
    multi-branch distance.

    Returns:
        {
            total_orders,
            multi_branch_avg_distance,
            single_kitchen_avg_distance,
            multi_branch_avg_delivery_time,
            single_kitchen_avg_delivery_time,
            distance_improvement_percentage,
            time_improvement_percentage,
        }
    """
    try:
        all_orders = list(orders.find(
            {},
            {"user_lat": 1, "user_lng": 1, "distance_km": 1, "estimated_delivery_time": 1},
        ))
    except PyMongoError as exc:
        logger.error("DB_ERROR | get_comparison_metrics query failed: %s", exc)
        return {
            "total_orders": 0,
            "multi_branch_avg_distance": 0,
            "single_kitchen_avg_distance": 0,
            "multi_branch_avg_delivery_time": 0,
            "single_kitchen_avg_delivery_time": 0,
            "distance_improvement_percentage": 0,
            "time_improvement_percentage": 0,
        }

    if not all_orders:
        return {
            "total_orders": 0,
            "multi_branch_avg_distance": 0,
            "single_kitchen_avg_distance": 0,
            "multi_branch_avg_delivery_time": 0,
            "single_kitchen_avg_delivery_time": 0,
            "distance_improvement_percentage": 0,
            "time_improvement_percentage": 0,
        }

    multi_distances = []
    single_distances = []
    multi_times = []
    single_times = []

    for order in all_orders:
        # Actual multi-branch distance (already stored)
        mb_dist = order.get("distance_km", 0)
        multi_distances.append(mb_dist)
        multi_times.append(order.get("estimated_delivery_time", estimate_delivery_time(mb_dist)))

        # Hypothetical single-kitchen distance
        sk_dist = calculate_distance(
            order["user_lat"], order["user_lng"],
            CENTRAL_KITCHEN["lat"], CENTRAL_KITCHEN["lng"],
        )
        single_distances.append(sk_dist)
        single_times.append(estimate_delivery_time(sk_dist))

    n = len(all_orders)
    mb_avg_dist = round(sum(multi_distances) / n, 2)
    sk_avg_dist = round(sum(single_distances) / n, 2)
    mb_avg_time = round(sum(multi_times) / n, 2)
    sk_avg_time = round(sum(single_times) / n, 2)

    dist_improvement = round(
        ((sk_avg_dist - mb_avg_dist) / sk_avg_dist * 100) if sk_avg_dist else 0, 2
    )
    time_improvement = round(
        ((sk_avg_time - mb_avg_time) / sk_avg_time * 100) if sk_avg_time else 0, 2
    )

    return {
        "total_orders": n,
        "multi_branch_avg_distance": mb_avg_dist,
        "single_kitchen_avg_distance": sk_avg_dist,
        "multi_branch_avg_delivery_time": mb_avg_time,
        "single_kitchen_avg_delivery_time": sk_avg_time,
        "distance_improvement_percentage": dist_improvement,
        "time_improvement_percentage": time_improvement,
    }
