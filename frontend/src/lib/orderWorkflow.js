export const statusLabels = {
  placed: "Placed",
  accepted: "Accepted",
  in_transit: "In Transit",
  delivered: "Delivered",
  ready_for_pickup: "Ready for Pickup",
  collected: "Collected",
  cancelled: "Cancelled",
};

export const statusColors = {
  placed: "bg-amber-100 text-amber-800",
  accepted: "bg-blue-100 text-blue-800",
  in_transit: "bg-cyan-100 text-cyan-800",
  delivered: "bg-emerald-100 text-emerald-800",
  ready_for_pickup: "bg-orange-100 text-orange-800",
  collected: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-rose-100 text-rose-800",
};

export const isCompletedOrder = (order) =>
  order.status === "delivered" || order.status === "collected" || order.status === "cancelled";

export const canCancelOrder = (order) => !isCompletedOrder(order);

export const getNextOrderAction = (order) => {
  if (order.status === "placed") {
    return { label: "Accept Order", status: "accepted", className: "bg-blue-600 hover:bg-blue-700" };
  }

  if (order.fulfillment_mode === "takeaway") {
    if (order.status === "accepted") {
      return { label: "Mark Ready for Pickup", status: "ready_for_pickup", className: "bg-orange-600 hover:bg-orange-700" };
    }

    if (order.status === "ready_for_pickup") {
      return { label: "Mark Collected", status: "collected", className: "bg-emerald-600 hover:bg-emerald-700" };
    }

    return null;
  }

  if (order.status === "accepted") {
    return { label: "Mark In Transit", status: "in_transit", className: "bg-cyan-600 hover:bg-cyan-700" };
  }

  if (order.status === "in_transit") {
    return { label: "Mark Delivered", status: "delivered", className: "bg-emerald-600 hover:bg-emerald-700" };
  }

  return null;
};

export const getOrderTimeline = (order) => {
  const steps =
    order.fulfillment_mode === "takeaway"
      ? [
          { key: "placed", label: "Order placed" },
          { key: "accepted", label: "Kitchen accepted" },
          { key: "ready_for_pickup", label: "Ready for pickup" },
          { key: "collected", label: "Collected" },
        ]
      : [
          { key: "placed", label: "Order placed" },
          { key: "accepted", label: "Kitchen accepted" },
          { key: "in_transit", label: "Out for delivery" },
          { key: "delivered", label: "Delivered" },
        ];

  const currentIndex = steps.findIndex((step) => step.key === order.status);

  if (order.status === "cancelled") {
    return steps.map((step) => ({
      ...step,
      state: step.key === "placed" ? "complete" : "cancelled",
    }));
  }

  return steps.map((step, index) => ({
    ...step,
    state: index < currentIndex ? "complete" : index === currentIndex ? "current" : "upcoming",
  }));
};
