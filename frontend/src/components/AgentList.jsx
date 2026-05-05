const API_URL = "http://localhost:8000/api";

const priorityRank = { urgent: 0, high: 1, standard: 2 };

const formatOrderBadgeTone = (priority) => {
  if (priority === "urgent") {
    return "bg-rose-100 text-rose-700";
  }

  if (priority === "high") {
    return "bg-orange-100 text-orange-700";
  }

  return "bg-slate-100 text-slate-700";
};

const sortAssignedOrders = (left, right) => {
  if ((left.route_stop_number ?? Number.MAX_SAFE_INTEGER) !== (right.route_stop_number ?? Number.MAX_SAFE_INTEGER)) {
    return (left.route_stop_number ?? Number.MAX_SAFE_INTEGER) - (right.route_stop_number ?? Number.MAX_SAFE_INTEGER);
  }

  return (priorityRank[left.priority] ?? 3) - (priorityRank[right.priority] ?? 3);
};

const buildRouteGroups = (assignedOrders) => {
  const groups = [];

  assignedOrders.forEach((order) => {
    const lastGroup = groups[groups.length - 1];
    if (order.assigned_batch_id && lastGroup?.batchId === order.assigned_batch_id) {
      lastGroup.orders.push(order);
      return;
    }

    groups.push({
      batchId: order.assigned_batch_id || null,
      orders: [order],
    });
  });

  return groups;
};

export default function AgentList({ agents, orders, onRefresh }) {
  const handleDelete = async (agentId) => {
    if (!confirm("Are you sure you want to delete this agent?")) return;

    try {
      const res = await fetch(`${API_URL}/agents/${agentId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("Failed to delete agent");
      }

      onRefresh();
      alert("Agent deleted successfully");
    } catch (err) {
      alert(`Error deleting agent: ${err.message}`);
    }
  };

  if (agents.length === 0) {
    return (
      <div className="py-8 text-center text-gray-500">
        <p className="text-lg">No agents yet. Create one to get started.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {agents.map((agent) => {
        const assignedOrders = orders
          .filter((order) => order.assigned_agent_id === agent.id && order.status !== "delivered" && order.status !== "cancelled")
          .sort(sortAssignedOrders);
        const busiestPriority = assignedOrders[0]?.priority || "standard";
        const routeGroups = buildRouteGroups(assignedOrders);

        return (
          <div
            key={agent.id}
            className="rounded-[28px] border border-slate-200 bg-white p-5 transition hover:shadow-lg"
          >
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-black text-slate-900">{agent.name}</h3>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Rider ID {agent.id.slice(-6)}</p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  agent.available ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
                }`}
              >
                {agent.status}
              </span>
            </div>

            <div className="mb-4 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-slate-950 px-4 py-3 text-white">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Load</p>
                <p className="mt-1 text-2xl font-black">{assignedOrders.length}</p>
                <p className="text-xs text-slate-300">Active stops now</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Priority mix</p>
                <p className="mt-1 text-lg font-black text-slate-900 capitalize">{busiestPriority}</p>
                <p className="text-xs text-slate-500">Highest active urgency</p>
              </div>
            </div>

            <div className="mb-4 space-y-2 text-sm text-slate-600">
              <p>
                Lat: <strong>{agent.lat.toFixed(4)}</strong>
              </p>
              <p>
                Lng: <strong>{agent.lng.toFixed(4)}</strong>
              </p>
              <p>
                Lifetime deliveries: <strong>{agent.total_deliveries || 0}</strong>
              </p>
              <p>
                Rating: <strong>{agent.avg_rating?.toFixed(1) || "5.0"}/5</strong>
              </p>
            </div>

            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Assigned route</p>
              {assignedOrders.length === 0 ? (
                <div className="mt-3 rounded-2xl border border-dashed border-slate-200 px-4 py-4 text-sm text-slate-500">
                  No active orders assigned right now.
                </div>
              ) : (
                <div className="mt-3 space-y-2">
                  {routeGroups.map((group, index) => (
                    <div key={`${agent.id}-${group.batchId || group.orders[0].id}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-white px-2 py-1 text-[11px] font-bold text-slate-700 ring-1 ring-slate-200">
                              {group.orders.length > 1
                                ? `Stops ${group.orders[0].route_stop_number}-${group.orders[group.orders.length - 1].route_stop_number}`
                                : `Stop ${group.orders[0].route_stop_number ?? index + 1}`}
                            </span>
                            <p className="font-semibold text-slate-900">
                              {group.orders.length > 1 ? `Nearby batch (${group.orders.length} drops)` : `Order #${group.orders[0].id.slice(-6)}`}
                            </p>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            {group.orders.length > 1
                              ? "Grouped because the drops are close together and should be ready around the same time."
                              : `${group.orders[0].customer_name || "Guest"} | ${group.orders[0].delivery_area || "Direct drop"}`}
                          </p>
                        </div>
                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${formatOrderBadgeTone(group.orders[0].priority)}`}>
                          {group.orders[0].priority}
                        </span>
                      </div>

                      {group.orders.length > 1 ? (
                        <div className="mt-3 space-y-2">
                          {group.orders.map((order) => (
                            <div key={order.id} className="rounded-2xl bg-white px-3 py-3 ring-1 ring-slate-200">
                              <div className="flex items-center justify-between gap-3">
                                <div>
                                  <p className="font-semibold text-slate-900">
                                    Stop {order.route_stop_number} | Order #{order.id.slice(-6)}
                                  </p>
                                  <p className="mt-1 text-xs text-slate-500">
                                    {order.customer_name || "Guest"} | {order.delivery_area || "Direct drop"}
                                  </p>
                                </div>
                                <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700">
                                  Batch stop {order.batch_stop_number}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => handleDelete(agent.id)}
              className="w-full rounded-2xl bg-red-100 py-2 text-sm font-medium text-red-700 hover:bg-red-200"
            >
              Delete Agent
            </button>
          </div>
        );
      })}
    </div>
  );
}
