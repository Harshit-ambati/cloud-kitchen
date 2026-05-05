"""
optimize_branches.py
--------------------
Uses K-Means clustering on the simulated delivery orders to find the
mathematically optimal locations for 5 kitchen branches.

Usage (from backend/):
    python -m app.scripts.optimize_branches
"""

import sys
import os
import logging
import numpy as np
from sklearn.cluster import KMeans

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.db import orders, db
from app.services.branches import BRANCHES
from app.services.distance import haversine

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

def run_optimization():
    # 1. Fetch all order coordinates (using simulated data for volume)
    cursor = orders.find({"is_simulated": True, "user_lat": {"$ne": None}, "user_lng": {"$ne": None}})
    order_coords = []
    for doc in cursor:
        order_coords.append([doc["user_lat"], doc["user_lng"]])
    
    if len(order_coords) < 5:
        logger.error("Not enough orders to perform clustering. Run simulate_orders.py first.")
        return

    X = np.array(order_coords)
    logger.info(f"Loaded {len(X)} simulated orders for clustering.")

    # 2. Run K-Means Clustering
    k = 5
    logger.info(f"Running K-Means clustering to find {k} optimal branch locations...")
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X)
    
    cluster_centers = kmeans.cluster_centers_

    # 3. Store optimized branches
    optimized_branches_coll = db["optimized_branches"]
    optimized_branches_coll.delete_many({})  # clear old data

    opt_branches_data = []
    for i, center in enumerate(cluster_centers):
        opt_branches_data.append({
            "id": f"opt_{i+1}",
            "name": f"Optimized Hub {i+1}",
            "lat": float(center[0]),
            "lng": float(center[1])
        })
    
    optimized_branches_coll.insert_many(opt_branches_data)
    logger.info("Saved optimized branches to MongoDB.")

    # 4. Compare distances
    current_total_dist = 0
    optimized_total_dist = 0
    
    for lat, lng in X:
        # Distance to nearest current branch
        min_curr = min(haversine(lat, lng, b["lat"], b["lng"]) for b in BRANCHES)
        current_total_dist += min_curr
        
        # Distance to nearest optimized branch
        min_opt = min(haversine(lat, lng, b["lat"], b["lng"]) for b in opt_branches_data)
        optimized_total_dist += min_opt

    current_avg = current_total_dist / len(X)
    optimized_avg = optimized_total_dist / len(X)
    improvement = ((current_avg - optimized_avg) / current_avg) * 100

    logger.info("--- OPTIMIZATION RESULTS ---")
    logger.info(f"Current Avg Distance:   {current_avg:.2f} km")
    logger.info(f"Optimized Avg Distance: {optimized_avg:.2f} km")
    logger.info(f"Improvement:            {improvement:.1f}% reduction in travel distance")
    logger.info("----------------------------")
    
    return {
        "current_avg_distance": current_avg,
        "optimized_avg_distance": optimized_avg,
        "improvement_percentage": improvement
    }

if __name__ == "__main__":
    run_optimization()
