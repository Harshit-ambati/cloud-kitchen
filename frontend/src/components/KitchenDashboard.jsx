import { useMemo } from "react";
import { canCancelOrder, getNextOrderAction, statusColors, statusLabels } from "../lib/orderWorkflow";

const API_URL = "http://localhost:8000/api";
const priorityColors = {
  standard: "bg-slate-100 text-slate-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-rose-100 text-rose-700",
};

const queueConfig = [
  {
    key: "delivery",
    title: "Delivery Queue",
    subtitle: "Kitchen orders that will move into rider dispatch.",
    filter: (order) => order.fulfillment_mode !== "takeaway" && order.status !== "delivered" && order.status !== "cancelled",
    empty: "No active delivery orders in the kitchen queue.",
  },
  {
    key: "takeaway",
    title: "Takeaway Queue",
    subtitle: "Pickup orders waiting to be prepared or collected.",
    filter: (order) => order.fulfillment_mode === "takeaway" && order.status !== "collected" && order.status !== "cancelled",
    empty: "No active takeaway orders waiting in the kitchen.",
  },
];

const formatDateTime = (value) => (value ? new Date(value).toLocaleString() : "Not available");
const formatPrice = (value) => `Rs. ${(value || 0).toFixed(0)}`;

const priorityRank = {
  urgent: 0,
  high: 1,
  standard: 2,
};

const getTargetTimestamp = (order) => {
  if (order.fulfillment_mode === "takeaway" && order.pickup_ready_at) {
    return new Date(order.pickup_ready_at).getTime();
  }

  if (order.created_at && typeof order.predicted_eta_minutes === "number") {
    return new Date(order.created_at).getTime() + order.predicted_eta_minutes * 60 * 1000;
  }

  return new Date(order.created_at || 0).getTime();
};

const sortKitchenOrders = (left, right) => {
  const leftPriority = priorityRank[left.priority] ?? 3;
  const rightPriority = priorityRank[right.priority] ?? 3;

  if (leftPriority !== rightPriority) {
    return leftPriority - rightPriority;
  }

  return getTargetTimestamp(left) - getTargetTimestamp(right);
};

const getStageLabel = (order) => {
  if (order.fulfillment_mode === "takeaway") {
    if (order.status === "placed") {
      return "New pickup order waiting for kitchen acceptance";
    }

    if (order.status === "accepted") {
      return "Being prepared for customer pickup";
    }

    if (order.status === "ready_for_pickup") {
      return "Prepared and waiting at the counter";
    }

    return "Takeaway workflow";
  }

  if (order.status === "placed") {
    return "New delivery order waiting for kitchen acceptance";
  }

  if (order.status === "accepted") {
    return order.assigned_agent_name ? "Kitchen is preparing before rider handoff" : "Kitchen is preparing while rider assignment catches up";
  }

  if (order.status === "in_transit") {
    return order.assigned_agent_name ? `Handed off to ${order.assigned_agent_name}` : "Marked in transit";
  }

  return "Delivery workflow";
};

const getAttentionNote = (order) => {
  if (order.fulfillment_mode !== "takeaway" && order.status === "placed" && order.assignment_status === "unassigned") {
    return {
      label: "Needs rider flow",
      className: "bg-slate-950 text-white",
    };
  }

  if (order.priority === "urgent") {
    return {
      label: "Rush order",
      className: "bg-rose-600 text-white",
    };
  }

  if (order.fulfillment_mode === "takeaway" && order.status === "ready_for_pickup") {
    return {
      label: "Waiting at counter",
      className: "bg-orange-500 text-white",
    };
  }

  return null;
};

const getQueueSections = (queueKey, queueOrders) => {
  const prepStatuses = ["placed", "accepted"];
  const handoffStatuses = queueKey === "takeaway" ? ["ready_for_pickup"] : ["in_transit"];

  return [
    {
      key: "prep",
      title: queueKey === "takeaway" ? "Prep Stage" : "Prep & Dispatch Stage",
      subtitle:
        queueKey === "takeaway"
          ? "Orders the kitchen still needs to accept or finish preparing."
          : "Orders still inside the kitchen before the final delivery handoff.",
      orders: queueOrders.filter((order) => prepStatuses.includes(order.status)).sort(sortKitchenOrders),
      empty: queueKey === "takeaway" ? "No pickup orders are waiting in prep." : "No delivery orders are waiting in prep.",
    },
    {
      key: "handoff",
      title: queueKey === "takeaway" ? "Pickup Counter" : "Out for Delivery",
      subtitle:
        queueKey === "takeaway"
          ? "Prepared pickup orders now waiting for customer collection."
          : "Orders already handed off and moving through the last-mile stage.",
      orders: queueOrders.filter((order) => handoffStatuses.includes(order.status)).sort(sortKitchenOrders),
      empty:
        queueKey === "takeaway"
          ? "Nothing is waiting at the pickup counter."
          : "No orders are currently in the rider handoff stage.",
    },
  ];
};

const queueTone = (order) => {
  if (order.priority === "urgent") {
    return "border-rose-200 bg-rose-50";
  }

  if (order.status === "ready_for_pickup") {
    return "border-orange-200 bg-orange-50";
  }

  if (order.status === "accepted") {
    return "border-blue-200 bg-blue-50";
  }

  if (order.status === "in_transit") {
    return "border-cyan-200 bg-cyan-50";
  }

  return "border-slate-200 bg-white";
};

export default function KitchenDashboard({ orders, onRefresh }) {
  const queueData = useMemo(
    () =>
      queueConfig.map((queue) => ({
        ...queue,
        orders: orders.filter(queue.filter).sort(sortKitchenOrders),
      })),
    [orders],
  );

  const kitchenStats = useMemo(() => {
    const preparing = orders.filter((order) => order.status === "accepted").length;
    const handoff = orders.filter((order) => order.status === "ready_for_pickup" || order.status === "in_transit").length;
    const needsDispatch = orders.filter(
      (order) =>
        order.priority === "urgent" ||
        (order.fulfillment_mode !== "takeaway" && order.assignment_status === "unassigned" && order.status === "placed"),
    ).length;

    return {
      preparing,
      handoff,
      needsDispatch,
    };
  }, [orders]);

  const updateStatus = async (orderId, status) => {
    try {
      const res = await fetch(`${API_URL}/orders/${orderId}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (!res.ok) {
        throw new Error("Failed to update status");
      }

      onRefresh();
    } catch (err) {
      alert(`Kitchen action failed: ${err.message}`);
    }
  };

  return (
    <section className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[28px] bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-600">Preparing Now</p>
          <p className="mt-3 text-3xl font-black text-slate-950">{kitchenStats.preparing}</p>
          <p className="mt-2 text-sm text-slate-500">Orders the kitchen has accepted and is actively working on.</p>
        </div>
        <div className="rounded-[28px] bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-600">Handoff Stage</p>
          <p className="mt-3 text-3xl font-black text-slate-950">{kitchenStats.handoff}</p>
          <p className="mt-2 text-sm text-slate-500">Orders waiting at pickup or already handed over for delivery.</p>
        </div>
        <div className="rounded-[28px] bg-slate-950 p-5 text-white shadow-[0_18px_50px_rgba(15,23,42,0.18)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-200">Needs Attention</p>
          <p className="mt-3 text-3xl font-black">{kitchenStats.needsDispatch}</p>
          <p className="mt-2 text-sm text-slate-300">Rush orders and delivery orders still waiting on rider flow or quick kitchen action.</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {queueData.map((queue) => (
          <section
            key={queue.key}
            className="rounded-[32px] bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-orange-600">{queue.title}</p>
                <h2 className="mt-2 text-3xl font-black text-slate-950">{queue.orders.length} active</h2>
                <p className="mt-2 text-sm text-slate-500">{queue.subtitle}</p>
              </div>
            </div>

            <div className="mt-5 space-y-4">
              {queue.orders.length === 0 ? (
                <div className="rounded-[24px] border border-dashed border-slate-200 px-5 py-10 text-center text-sm text-slate-500">
                  {queue.empty}
                </div>
              ) : (
                getQueueSections(queue.key, queue.orders).map((section) => (
                  <div key={`${queue.key}-${section.key}`} className="space-y-3">
                    <div className="flex items-center justify-between gap-3 rounded-[22px] bg-slate-50 px-4 py-3 ring-1 ring-slate-200">
                      <div>
                        <p className="text-sm font-black text-slate-900">{section.title}</p>
                        <p className="mt-1 text-xs text-slate-500">{section.subtitle}</p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                        {section.orders.length} orders
                      </span>
                    </div>

                    {section.orders.length === 0 ? (
                      <div className="rounded-[24px] border border-dashed border-slate-200 px-5 py-6 text-center text-sm text-slate-500">
                        {section.empty}
                      </div>
                    ) : (
                      section.orders.map((order) => {
                        const action = getNextOrderAction(order);
                        const attentionNote = getAttentionNote(order);

                        return (
                          <article
                            key={order.id}
                            className={`rounded-[26px] border p-5 shadow-sm transition ${queueTone(order)}`}
                          >
                            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                              <div className="space-y-3">
                                <div className="flex flex-wrap items-center gap-2">
                                  <h3 className="text-xl font-black text-slate-950">Order #{order.id.slice(-6)}</h3>
                                  <span
                                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                      priorityColors[order.priority] || "bg-slate-100 text-slate-700"
                                    }`}
                                  >
                                    {order.priority || "standard"}
                                  </span>
                                  <span
                                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                      statusColors[order.status] || "bg-slate-100 text-slate-700"
                                    }`}
                                  >
                                    {statusLabels[order.status] || order.status}
                                  </span>
                                  <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-semibold capitalize text-slate-700 ring-1 ring-slate-200">
                                    {order.fulfillment_mode}
                                  </span>
                                  {attentionNote ? (
                                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${attentionNote.className}`}>
                                      {attentionNote.label}
                                    </span>
                                  ) : null}
                                </div>

                                <div className="grid gap-2 text-sm text-slate-600">
                                  <p>
                                    Customer: <span className="font-semibold text-slate-900">{order.customer_name || "Guest"}</span>
                                  </p>
                                  <p>
                                    Stage note: <span className="font-semibold text-slate-900">{getStageLabel(order)}</span>
                                  </p>
                                  <p>
                                    Kitchen target:{" "}
                                    <span className="font-semibold text-slate-900">
                                      {order.fulfillment_mode === "takeaway"
                                        ? formatDateTime(order.pickup_ready_at)
                                        : `${order.predicted_eta_minutes} min total ETA`}
                                    </span>
                                  </p>
                                  <p>
                                    Next handoff:{" "}
                                    <span className="font-semibold text-slate-900">
                                      {order.fulfillment_mode === "takeaway"
                                        ? "Customer collection at restaurant"
                                        : order.assigned_agent_name || "Waiting for rider assignment"}
                                    </span>
                                  </p>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                  {(order.items || []).map((item) => (
                                    <span
                                      key={`${order.id}-${item.dish_id}`}
                                      className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200"
                                    >
                                      {item.name} x{item.quantity}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              <div className="rounded-[22px] bg-white/90 px-4 py-4 text-sm text-slate-700 ring-1 ring-slate-200 md:min-w-56">
                                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Kitchen Summary</p>
                                <p className="mt-2 text-2xl font-black text-slate-950">{formatPrice(order.total_amount)}</p>
                                <p className="mt-2">
                                  Prep: <span className="font-semibold text-slate-900">{order.predicted_prep_minutes} min</span>
                                </p>
                                <p>
                                  Items: <span className="font-semibold text-slate-900">{order.item_count || 0}</span>
                                </p>
                                <p>
                                  Created: <span className="font-semibold text-slate-900">{formatDateTime(order.created_at)}</span>
                                </p>
                              </div>
                            </div>

                            <div className="mt-5 flex flex-wrap gap-3">
                              {action ? (
                                <button
                                  type="button"
                                  onClick={() => updateStatus(order.id, action.status)}
                                  className={`rounded-full px-4 py-2 text-sm font-bold text-white transition ${action.className}`}
                                >
                                  {action.label}
                                </button>
                              ) : null}
                              {canCancelOrder(order) ? (
                                <button
                                  type="button"
                                  onClick={() => updateStatus(order.id, "cancelled")}
                                  className="rounded-full bg-rose-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-rose-700"
                                >
                                  Cancel Order
                                </button>
                              ) : null}
                            </div>
                          </article>
                        );
                      })
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
