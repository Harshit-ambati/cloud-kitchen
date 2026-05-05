import math
from datetime import datetime


LOAD_PENALTY_KM = 2.5
HIGH_PRIORITY_BONUS_KM = 1.0
URGENT_PRIORITY_BONUS_KM = 2.0
BATCH_DISTANCE_THRESHOLD_KM = 2.5
BATCH_READY_WINDOW_MINUTES = 12
MAX_BATCH_SIZE = 3
BATCH_EFFICIENCY_BONUS_KM = 0.9


def haversine(lat1, lon1, lat2, lon2):
    radius_km = 6371
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(delta_lon / 2) ** 2
    )
    return radius_km * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def distance_km(origin, destination):
    return haversine(origin[0], origin[1], destination[0], destination[1])


def order_location(order):
    return (order["user_lat"], order["user_lng"])


def agent_location(agent):
    return (agent["lat"], agent["lng"])


def normalize_agent_load(agent):
    return max(agent.get("current_load", 0), len(agent.get("active_order_ids", [])))


def order_priority_rank(order):
    return {
        "urgent": 0,
        "high": 1,
        "standard": 2,
    }.get(order.get("priority", "standard"), 2)


def order_priority_bonus(order):
    if order.get("priority") == "urgent":
        return URGENT_PRIORITY_BONUS_KM
    if order.get("priority") == "high":
        return HIGH_PRIORITY_BONUS_KM
    return 0


def created_at_sort_key(order):
    created_at = order.get("created_at")
    if isinstance(created_at, datetime):
        return created_at.timestamp()
    if isinstance(created_at, (int, float)):
        return float(created_at)
    if isinstance(created_at, str):
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0
    return 0


def ready_time_score(order):
    return created_at_sort_key(order) + (order.get("predicted_prep_minutes", 0) * 60)


def batch_centroid_location(batch_orders):
    lat = sum(order["user_lat"] for order in batch_orders) / len(batch_orders)
    lng = sum(order["user_lng"] for order in batch_orders) / len(batch_orders)
    return (lat, lng)


def can_join_batch(anchor_order, candidate_order, current_batch):
    if order_priority_rank(anchor_order) != order_priority_rank(candidate_order):
        return False

    ready_gap_minutes = abs(ready_time_score(anchor_order) - ready_time_score(candidate_order)) / 60
    if ready_gap_minutes > BATCH_READY_WINDOW_MINUTES:
        return False

    current_centroid = batch_centroid_location(current_batch)
    return distance_km(current_centroid, order_location(candidate_order)) <= BATCH_DISTANCE_THRESHOLD_KM


def build_delivery_batches(orders):
    prioritized_orders = sorted(
        orders,
        key=lambda order: (order_priority_rank(order), created_at_sort_key(order)),
    )
    pending_orders = prioritized_orders[:]
    batches = []

    while pending_orders:
        anchor_order = pending_orders.pop(0)
        batch = [anchor_order]
        remaining_orders = []

        for candidate_order in pending_orders:
            if len(batch) < MAX_BATCH_SIZE and can_join_batch(anchor_order, candidate_order, batch):
                batch.append(candidate_order)
            else:
                remaining_orders.append(candidate_order)

        pending_orders = remaining_orders
        batches.append(batch)

    return batches


def score_agent_for_batch(agent, batch_orders, projected_load):
    centroid = batch_centroid_location(batch_orders)
    distance_score = distance_km(agent_location(agent), centroid)
    load_score = projected_load * LOAD_PENALTY_KM
    priority_bonus = order_priority_bonus(batch_orders[0])
    efficiency_bonus = max(0, len(batch_orders) - 1) * BATCH_EFFICIENCY_BONUS_KM
    return distance_score + load_score - priority_bonus - efficiency_bonus


def build_route_for_batch(start_location, batch_orders):
    route = []
    remaining_orders = batch_orders[:]
    current_location = start_location

    while remaining_orders:
        next_order = min(
            remaining_orders,
            key=lambda order: distance_km(current_location, order_location(order)),
        )
        route.append(next_order)
        current_location = order_location(next_order)
        remaining_orders.remove(next_order)

    return route


def build_agent_route_batches(start_location, assigned_batches):
    route_batches = []
    remaining_batches = assigned_batches[:]
    current_location = start_location

    while remaining_batches:
        next_batch = min(
            remaining_batches,
            key=lambda batch: distance_km(current_location, batch_centroid_location(batch)),
        )
        ordered_batch = build_route_for_batch(current_location, next_batch)
        route_batches.append(ordered_batch)
        current_location = order_location(ordered_batch[-1])
        remaining_batches.remove(next_batch)

    return route_batches


def optimize_routes(orders, agents):
    if not orders or not agents:
        return {}

    routes = {agent["id"]: [] for agent in agents}
    loads = {agent["id"]: normalize_agent_load(agent) for agent in agents}
    batches = build_delivery_batches(orders)

    for batch_orders in batches:
        ranked_agents = sorted(
            agents,
            key=lambda agent: (
                score_agent_for_batch(agent, batch_orders, loads[agent["id"]]),
                loads[agent["id"]],
                distance_km(agent_location(agent), batch_centroid_location(batch_orders)),
            ),
        )
        selected_agent = ranked_agents[0]
        routes[selected_agent["id"]].append(batch_orders)
        loads[selected_agent["id"]] += len(batch_orders)

    for agent in agents:
        agent_id = agent["id"]
        routes[agent_id] = build_agent_route_batches(agent_location(agent), routes[agent_id])

    return routes
