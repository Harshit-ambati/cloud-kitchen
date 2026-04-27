import { useEffect, useMemo, useState } from "react";
import { canCancelOrder, getNextOrderAction, getOrderTimeline, statusColors, statusLabels } from "../lib/orderWorkflow";

const API_URL = "http://localhost:8000/api";

const priorityColors = {
  standard: "bg-slate-100 text-slate-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-rose-100 text-rose-700",
};

const timelineTone = {
  complete: "bg-emerald-500 border-emerald-500 text-emerald-700",
  current: "bg-orange-500 border-orange-500 text-orange-700",
  upcoming: "bg-white border-slate-300 text-slate-400",
  cancelled: "bg-rose-100 border-rose-200 text-rose-500",
};

const formatPrice = (value) => `Rs. ${(value || 0).toFixed(2)}`;
const formatDateTime = (value) => (value ? new Date(value).toLocaleString() : "Not available");

export default function OrderList({ orders, onRefresh, highlightedOrderId }) {
  const [expandedId, setExpandedId] = useState(null);

  const highlightedOrder = useMemo(
    () => orders.find((order) => order.id === highlightedOrderId) || null,
    [highlightedOrderId, orders],
  );

  useEffect(() => {
    if (highlightedOrderId) {
      setExpandedId(highlightedOrderId);
    }
  }, [highlightedOrderId]);

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
      alert(`Error updating status: ${err.message}`);
    }
  };

  if (orders.length === 0) {
    return (
      <div className="rounded-[28px] bg-white px-6 py-12 text-center text-slate-500 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
        <p className="text-lg font-semibold text-slate-700">No food orders yet</p>
        <p className="mt-2 text-sm">Start by adding dishes from the menu and placing a live order.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {highlightedOrder ? (
        <section className="overflow-hidden rounded-[30px] bg-[linear-gradient(135deg,#fff7ed_0%,#ffffff_45%,#eff6ff_100%)] p-6 shadow-[0_18px_50px_rgba(15,23,42,0.08)] ring-1 ring-orange-100">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-orange-600">Latest confirmation</p>
              <h3 className="mt-2 text-3xl font-black text-slate-950">
                Order #{highlightedOrder.id.slice(-6)} is {statusLabels[highlightedOrder.status]?.toLowerCase() || highlightedOrder.status}.
              </h3>
              <p className="mt-3 text-sm text-slate-600">
                {highlightedOrder.fulfillment_mode === "takeaway"
                  ? `Pickup is expected around ${formatDateTime(highlightedOrder.pickup_ready_at)} at Cloud Kitchen Express, Hyderabad.`
                  : `Your rider flow is running. Current ETA is about ${highlightedOrder.predicted_eta_minutes} minutes for ${highlightedOrder.delivery_area || "your drop location"}.`}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(highlightedOrder.items || []).map((item) => (
                  <span
                    key={`highlight-${highlightedOrder.id}-${item.dish_id}`}
                    className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200"
                  >
                    {item.name} x{item.quantity}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] bg-slate-950 px-5 py-5 text-white lg:min-w-72">
              <p className="text-xs uppercase tracking-[0.2em] text-orange-200">Order summary</p>
              <p className="mt-2 text-3xl font-black">{formatPrice(highlightedOrder.total_amount)}</p>
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-300">
                <p>
                  Items
                  <span className="mt-1 block font-semibold text-white">{highlightedOrder.item_count || 0}</span>
                </p>
                <p>
                  Mode
                  <span className="mt-1 block font-semibold capitalize text-white">{highlightedOrder.fulfillment_mode}</span>
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-4">
            {getOrderTimeline(highlightedOrder).map((step, index, steps) => (
              <div key={`${highlightedOrder.id}-${step.key}`} className="relative rounded-[22px] bg-white px-4 py-4 ring-1 ring-slate-200">
                {index < steps.length - 1 ? (
                  <div className="absolute left-[calc(100%-0.5rem)] top-7 hidden h-[2px] w-8 bg-slate-200 md:block" />
                ) : null}
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex h-4 w-4 rounded-full border-2 ${timelineTone[step.state] || timelineTone.upcoming}`}
                  />
                  <p className="text-sm font-bold text-slate-900">{step.label}</p>
                </div>
                <p className="mt-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  {step.state === "current"
                    ? "Current step"
                    : step.state === "complete"
                      ? "Completed"
                      : step.state === "cancelled"
                        ? "Stopped"
                        : "Coming up"}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {orders.map((order) => {
        const nextAction = getNextOrderAction(order);
        const timeline = getOrderTimeline(order);

        return (
          <article
            key={order.id}
            className={`rounded-[30px] bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ${
              order.id === highlightedOrderId ? "ring-orange-300" : "ring-slate-200"
            }`}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-xl font-black text-slate-900">Order #{order.id.slice(-6)}</h3>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      priorityColors[order.priority] || "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {order.priority}
                  </span>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      statusColors[order.status] || "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {statusLabels[order.status] || order.status}
                  </span>
                </div>

                <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
                  <p>
                    Customer: <span className="font-semibold text-slate-900">{order.customer_name || "Guest"}</span>
                  </p>
                  <p>
                    Mode: <span className="font-semibold capitalize text-slate-900">{order.fulfillment_mode || "delivery"}</span>
                  </p>
                  <p>
                    {order.fulfillment_mode === "takeaway" ? "Ready by" : "ETA"}:{" "}
                    <span className="font-semibold text-slate-900">
                      {order.fulfillment_mode === "takeaway"
                        ? formatDateTime(order.pickup_ready_at)
                        : `${order.predicted_eta_minutes} min`}
                    </span>
                  </p>
                  <p>
                    {order.fulfillment_mode === "takeaway" ? "Pickup point" : "Rider"}:{" "}
                    <span className="font-semibold text-slate-900">
                      {order.fulfillment_mode === "takeaway"
                        ? "Cloud Kitchen Express"
                        : order.assigned_agent_name || "Unassigned"}
                    </span>
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {(order.items || []).slice(0, 3).map((item) => (
                    <span
                      key={`${order.id}-${item.dish_id}`}
                      className="rounded-full bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-700 ring-1 ring-orange-100"
                    >
                      {item.name} x{item.quantity}
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid gap-3 rounded-[24px] bg-slate-950 px-5 py-4 text-sm text-white lg:min-w-60">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Bill amount</p>
                  <p className="mt-1 text-2xl font-black">{formatPrice(order.total_amount)}</p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-slate-300">
                  <p>
                    Items
                    <span className="mt-1 block font-semibold text-white">{order.item_count || 0}</span>
                  </p>
                  <p>
                    {order.fulfillment_mode === "takeaway" ? "Pickup" : "Distance"}
                    <span className="mt-1 block font-semibold text-white">
                      {order.fulfillment_mode === "takeaway" ? "At restaurant" : `${order.distance_km?.toFixed(2)} km`}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            {expandedId === order.id ? (
              <div className="mt-5 grid gap-5 border-t border-slate-200 pt-5 xl:grid-cols-[1.3fr_0.7fr]">
                <div>
                  <h4 className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">Tracking progress</h4>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {timeline.map((step) => (
                      <div key={`${order.id}-${step.key}-timeline`} className="rounded-2xl bg-slate-50 px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span
                            className={`inline-flex h-4 w-4 rounded-full border-2 ${timelineTone[step.state] || timelineTone.upcoming}`}
                          />
                          <p className="font-semibold text-slate-900">{step.label}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <h4 className="mt-5 text-sm font-black uppercase tracking-[0.2em] text-slate-500">Order items</h4>
                  <div className="mt-3 space-y-3">
                    {(order.items || []).map((item) => (
                      <div
                        key={`${order.id}-${item.dish_id}-detail`}
                        className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
                      >
                        <div>
                          <p className="font-semibold text-slate-900">{item.name}</p>
                          <p className="text-sm text-slate-500">
                            {item.category} - {item.quantity} x Rs. {item.unit_price}
                          </p>
                        </div>
                        <p className="font-bold text-slate-900">{formatPrice(item.line_total)}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-3 rounded-[24px] bg-orange-50 p-4 text-sm text-slate-700 ring-1 ring-orange-100">
                  <p>
                    Address: <span className="font-semibold text-slate-900">{order.delivery_address || "Not provided"}</span>
                  </p>
                  <p>
                    Phone: <span className="font-semibold text-slate-900">{order.customer_phone || "Not provided"}</span>
                  </p>
                  <p>
                    Prep: <span className="font-semibold text-slate-900">{order.predicted_prep_minutes} min</span>
                  </p>
                  <p>
                    Travel: <span className="font-semibold text-slate-900">{order.predicted_travel_minutes} min</span>
                  </p>
                  {order.fulfillment_mode === "takeaway" ? (
                    <p>
                      Pickup ready at: <span className="font-semibold text-slate-900">{formatDateTime(order.pickup_ready_at)}</span>
                    </p>
                  ) : null}
                  <p>
                    Delivery + platform + GST:{" "}
                    <span className="font-semibold text-slate-900">
                      {formatPrice(order.delivery_fee + order.platform_fee + order.taxes)}
                    </span>
                  </p>
                  <p>
                    GST & restaurant charges:{" "}
                    <span className="font-semibold text-slate-900">{formatPrice(order.taxes)} (5% of item total)</span>
                  </p>
                  <p>
                    Created: <span className="font-semibold text-slate-900">{new Date(order.created_at).toLocaleString()}</span>
                  </p>

                  <div className="flex flex-wrap gap-2 pt-2">
                    {nextAction ? (
                      <button
                        onClick={() => updateStatus(order.id, nextAction.status)}
                        className={`rounded-full px-3 py-2 text-xs font-bold text-white ${nextAction.className}`}
                      >
                        {nextAction.label}
                      </button>
                    ) : null}
                    {canCancelOrder(order) ? (
                      <button
                        onClick={() => updateStatus(order.id, "cancelled")}
                        className="rounded-full bg-rose-600 px-3 py-2 text-xs font-bold text-white hover:bg-rose-700"
                      >
                        Cancel
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            <button
              onClick={() => setExpandedId(expandedId === order.id ? null : order.id)}
              className="mt-5 text-sm font-bold text-orange-600 hover:text-orange-700"
            >
              {expandedId === order.id ? "Hide order details" : "View order details"}
            </button>
          </article>
        );
      })}
    </div>
  );
}
