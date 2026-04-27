from ml.route_optimizer import optimize_routes


def assign_orders(orders, agents):
    if not orders or not agents:
        return {}

    routes = optimize_routes(orders, agents)
    assignments = {agent["id"]: [] for agent in agents}

    for agent_id, route in routes.items():
        assignments[agent_id] = [stop["id"] for stop in route]

    return assignments
