"""
simulate_orders.py
------------------
Generates 500-1000 random food delivery orders across Hyderabad,
routes each one through the existing assign_branch() logic, and
persists the results in MongoDB with is_simulated = True.

Usage (from the `backend/` directory):
    python -m app.scripts.simulate_orders
    python -m app.scripts.simulate_orders --count 750
    python -m app.scripts.simulate_orders --count 1000 --clear
"""

import argparse
import logging
import random
import sys
import os
from datetime import datetime, timedelta

# ── make sure project root is on sys.path ──────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.db import orders
from app.services.branch_selector import assign_branch
from app.services.distance import haversine
from app.services.metrics import estimate_delivery_time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Hyderabad bounding box ─────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 17.20, 17.60
LNG_MIN, LNG_MAX = 78.20, 78.60

# ── Simulated customer name pool ───────────────────────────────────────────────
NAMES = [
    "Aarav Sharma", "Priya Reddy", "Kiran Kumar", "Meena Patel",
    "Rahul Gupta", "Sneha Rao", "Vikram Singh", "Divya Nair",
    "Arun Krishnan", "Pooja Mehta", "Suresh Iyer", "Ananya Desai",
    "Ravi Varma", "Lakshmi Pillai", "Sanjay Bhat", "Kavita Joshi",
    "Arjun Tiwari", "Swathi Reddy", "Naveen Goud", "Deepa Rao",
]

AREAS = [
    "Kukatpally", "HITEC City", "Gachibowli", "Madhapur", "Kondapur",
    "Secunderabad", "Begumpet", "Jubilee Hills", "Banjara Hills",
    "LB Nagar", "Dilsukhnagar", "Kothapet", "Uppal", "Hayathnagar",
    "Mehdipatnam", "Tolichowki", "Manikonda", "Nanakramguda",
    "Miyapur", "JNTU", "Ameerpet", "Somajiguda", "SR Nagar",
]

DISH_POOL = [
    {"dish_id": "d01", "name": "Hyderabad Biryani",   "category": "Main",    "unit_price": 220},
    {"dish_id": "d02", "name": "Butter Chicken",       "category": "Main",    "unit_price": 190},
    {"dish_id": "d03", "name": "Masala Dosa",          "category": "Starter", "unit_price": 80},
    {"dish_id": "d04", "name": "Paneer Tikka",         "category": "Starter", "unit_price": 160},
    {"dish_id": "d05", "name": "Gulab Jamun",          "category": "Dessert", "unit_price": 60},
    {"dish_id": "d06", "name": "Chicken 65",           "category": "Starter", "unit_price": 175},
    {"dish_id": "d07", "name": "Dal Tadka",            "category": "Main",    "unit_price": 120},
    {"dish_id": "d08", "name": "Tandoori Roti",        "category": "Bread",   "unit_price": 25},
    {"dish_id": "d09", "name": "Veg Fried Rice",       "category": "Main",    "unit_price": 130},
    {"dish_id": "d10", "name": "Lassi",                "category": "Drink",   "unit_price": 55},
]


def random_items():
    """Pick 1-4 random dishes with random quantities."""
    chosen = random.sample(DISH_POOL, k=random.randint(1, 4))
    items = []
    for dish in chosen:
        qty = random.randint(1, 3)
        line_total = round(dish["unit_price"] * qty, 2)
        items.append({
            "dish_id": dish["dish_id"],
            "name": dish["name"],
            "category": dish["category"],
            "quantity": qty,
            "unit_price": dish["unit_price"],
            "line_total": line_total,
        })
    return items


def build_order_document(user_lat: float, user_lng: float) -> dict:
    """Build a complete MongoDB order document for one simulated order."""
    # Route through existing branch selector
    branch, distance_km = assign_branch(user_lat, user_lng)

    kitchen_lat = branch["lat"]
    kitchen_lng = branch["lng"]

    items        = random_items()
    subtotal     = round(sum(i["line_total"] for i in items), 2)
    delivery_fee = round(random.uniform(20, 60), 2)
    platform_fee = round(random.uniform(5, 15), 2)
    taxes        = round(subtotal * 0.05, 2)
    total_amount = round(subtotal + delivery_fee + platform_fee + taxes, 2)

    order_type   = random.choice(["regular", "express"])
    priority     = random.choice(["standard", "high"])
    prep_eta     = 12 if order_type == "express" else 18
    prep_eta    += min(len(items) * 2, 10)
    travel_eta   = round(distance_km / 0.5, 2)   # ~30 km/h equivalent in minutes
    eta_minutes  = round(prep_eta + travel_eta, 2)

    created_at = datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))

    return {
        # ── Location ────────────────────────────────────────────────────────
        "user_lat":    user_lat,
        "user_lng":    user_lng,
        "kitchen_lat": kitchen_lat,
        "kitchen_lng": kitchen_lng,
        "branch_id":   branch["id"],
        # ── Order meta ──────────────────────────────────────────────────────
        "fulfillment_mode":  "delivery",
        "order_type":        order_type,
        "priority":          priority,
        "customer_name":     random.choice(NAMES),
        "customer_phone":    f"+91-9{random.randint(100000000, 999999999)}",
        "delivery_area":     random.choice(AREAS),
        "delivery_address":  f"Flat {random.randint(1,20)}, {random.choice(AREAS)}, Hyderabad",
        "restaurant_name":   f"Cloud Kitchen – {branch['name']}",
        # ── Items ───────────────────────────────────────────────────────────
        "items":       items,
        "item_count":  sum(i["quantity"] for i in items),
        "subtotal":    subtotal,
        "delivery_fee":  delivery_fee,
        "platform_fee":  platform_fee,
        "taxes":         taxes,
        "total_amount":  total_amount,
        # ── Metrics ─────────────────────────────────────────────────────────
        "distance_km":             round(distance_km, 3),
        "estimated_delivery_time": estimate_delivery_time(distance_km),
        "predicted_prep_minutes":  prep_eta,
        "predicted_travel_minutes": travel_eta,
        "predicted_eta_minutes":   eta_minutes,
        # ── Status ──────────────────────────────────────────────────────────
        "status":            random.choice(["placed", "accepted", "in_transit", "delivered"]),
        "prep_status":       "completed",
        "assignment_status": "assigned",
        "assigned_agent_id":   None,
        "assigned_agent_name": None,
        "assigned_batch_id":   None,
        "assigned_batch_size": 1,
        "route_stop_number":   None,
        "batch_stop_number":   None,
        "batch_order_ids":     [],
        # ── Timestamps ──────────────────────────────────────────────────────
        "created_at": created_at,
        "updated_at": created_at,
        "estimated_delivery_at": created_at + timedelta(minutes=eta_minutes),
        "pickup_ready_at": None,
        # ── Simulation flag ─────────────────────────────────────────────────
        "is_simulated": True,
    }


def run_simulation(count: int = 750, clear_existing: bool = False):
    """
    Main entry point.

    Parameters
    ----------
    count           : number of simulated orders to generate (500-1000)
    clear_existing  : if True, delete previous simulated orders first
    """
    count = max(500, min(1000, count))

    if clear_existing:
        deleted = orders.delete_many({"is_simulated": True})
        logger.info("Cleared %d existing simulated orders.", deleted.deleted_count)

    logger.info("Starting simulation: generating %d orders …", count)

    branch_counter: dict[str, int] = {}
    batch_size = 100
    batch: list[dict] = []

    for i in range(count):
        lat = round(random.uniform(LAT_MIN, LAT_MAX), 6)
        lng = round(random.uniform(LNG_MIN, LNG_MAX), 6)

        doc = build_order_document(lat, lng)
        branch_counter[doc["branch_id"]] = branch_counter.get(doc["branch_id"], 0) + 1
        batch.append(doc)

        if len(batch) >= batch_size:
            orders.insert_many(batch)
            logger.info("  Inserted %d / %d orders …", i + 1, count)
            batch = []

    if batch:
        orders.insert_many(batch)

    logger.info("✅  Simulation complete.")
    logger.info("Distribution across branches:")
    for bid, cnt in sorted(branch_counter.items()):
        logger.info("   %-4s  → %d orders", bid, cnt)

    return branch_counter


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate delivery orders for cloud kitchen.")
    parser.add_argument(
        "--count", type=int, default=750,
        help="Number of orders to simulate (500-1000, default 750)",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Delete existing simulated orders before inserting new ones",
    )
    args = parser.parse_args()
    run_simulation(count=args.count, clear_existing=args.clear)
