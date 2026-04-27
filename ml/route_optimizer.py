import math


def distance_km(origin, destination):
    return math.dist(origin, destination) * 111


def order_location(order):
    return (order["user_lat"], order["user_lng"])


def agent_location(agent):
    return (agent["lat"], agent["lng"])


def optimize_routes(orders, agents):
    if not orders or not agents:
        return {}

    routes = {agent["id"]: [] for agent in agents}
    loads = {
        agent["id"]: len(agent.get("active_order_ids", [])) + agent.get("current_load", 0)
        for agent in agents
    }

    for order in sorted(orders, key=lambda item: (item.get("priority") != "urgent", item.get("created_at"))):
        ranked_agents = sorted(
            agents,
            key=lambda agent: (
                loads[agent["id"]],
                distance_km(agent_location(agent), order_location(order)),
            ),
        )
        selected_agent = ranked_agents[0]
        routes[selected_agent["id"]].append(order)
        loads[selected_agent["id"]] += 1

    for agent in agents:
        agent_id = agent["id"]
        start = agent_location(agent)
        routes[agent_id] = sorted(
            routes[agent_id],
            key=lambda order: distance_km(start, order_location(order)),
        )

    return routes
