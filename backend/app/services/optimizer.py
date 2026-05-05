from ml.route_optimizer import optimize_routes


def assign_orders(orders, agents):
    if not orders or not agents:
        return {}

    routes = optimize_routes(orders, agents)
    assignments = {agent["id"]: [] for agent in agents}

    for agent_id, route_batches in routes.items():
        assignments[agent_id] = [
            {
                "batch_id": f"{agent_id}-batch-{index}" if len(batch_orders) > 1 else None,
                "batch_size": len(batch_orders),
                "order_ids": [stop["id"] for stop in batch_orders],
            }
            for index, batch_orders in enumerate(route_batches, start=1)
        ]

    return assignments
