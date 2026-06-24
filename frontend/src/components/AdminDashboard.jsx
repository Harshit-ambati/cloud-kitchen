import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, Polyline, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import AgentForm from "./AgentForm";
import AgentList from "./AgentList";
import KitchenDashboard from "./KitchenDashboard";
import OrderForm from "./OrderForm";
import OrderList from "./OrderList";
import "../App.css";

const API_URL = "http://localhost:8000/api";
const KITCHEN_LOCATION = { lat: 17.385, lng: 78.4867 };
const formatDateTime = (value) => (value ? new Date(value).toLocaleString() : "Not available");

const tabs = [
  {
    id: "menu",
    label: "Menu",
    shortcut: "01",
    eyebrow: "Customer ordering",
    title: "Browse dishes and place orders",
    description: "Customer-facing ordering with live cart, service zones, pickup, and delivery checkout.",
  },
  {
    id: "kitchen",
    label: "Kitchen",
    shortcut: "02",
    eyebrow: "Kitchen control",
    title: "Prep queues for delivery and takeaway",
    description: "Accept, prepare, prioritize, and hand off delivery or pickup orders from one queue.",
  },
  {
    id: "orders",
    label: "Orders",
    shortcut: "03",
    eyebrow: "Live order queue",
    title: "Orders with dishes, billing, and delivery progress",
    description: "Track live status, itemized bills, route batches, customer details, and workflow actions.",
  },
  {
    id: "agents",
    label: "Fleet",
    shortcut: "04",
    eyebrow: "Delivery fleet",
    title: "Manage riders for the food-ordering flow",
    description: "Monitor rider availability, active load, route groups, and delivery capacity.",
  },
  {
    id: "map",
    label: "Live Map",
    shortcut: "05",
    eyebrow: "Operations map",
    title: "Kitchen, orders, and riders in real time",
    description: "Visualize the kitchen, rider positions, delivery routes, and pickup workload.",
  },
];

const statCards = (stats) => [
  { label: "Live Orders", value: stats.activeOrders, tone: "light" },
  { label: "Revenue", value: `Rs. ${stats.revenue.toFixed(0)}`, tone: "light" },
  { label: "Riders Free", value: stats.availableAgents, tone: "light" },
  { label: "Unassigned", value: stats.unassignedOrders, tone: "dark" },
];

const sortRouteOrders = (left, right) => {
  if ((left.route_stop_number ?? Number.MAX_SAFE_INTEGER) !== (right.route_stop_number ?? Number.MAX_SAFE_INTEGER)) {
    return (left.route_stop_number ?? Number.MAX_SAFE_INTEGER) - (right.route_stop_number ?? Number.MAX_SAFE_INTEGER);
  }

  return left.created_at > right.created_at ? 1 : -1;
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

export default function App({ currentUser, onLogout }) {
  const [orders, setOrders] = useState([]);
  const [agents, setAgents] = useState([]);
  const [activeTab, setActiveTab] = useState("menu");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);
  const [highlightedOrderId, setHighlightedOrderId] = useState(null);

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_URL}/orders/`);
      const data = await res.json();
      setOrders(data.orders || []);
    } catch (err) {
      console.error("Error fetching orders:", err);
    }
  };

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API_URL}/agents/`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (err) {
      console.error("Error fetching agents:", err);
    }
  };

  useEffect(() => {
    fetchOrders();
    fetchAgents();
    const interval = setInterval(() => {
      fetchOrders();
      fetchAgents();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleOrderCreated = (newOrder) => {
    setOrders((current) => {
      if (current.some((order) => order.id === newOrder.id)) {
        return current;
      }

      return [newOrder, ...current];
    });
    setHighlightedOrderId(newOrder.id);
  };

  const handleTrackOrder = (orderId) => {
    setHighlightedOrderId(orderId);
    setActiveTab("orders");
    setIsSidebarOpen(false);
  };

  const handleAgentCreated = (newAgent) => {
    setAgents((current) => [newAgent, ...current]);
  };

  const optimizeAssignments = async () => {
    setIsDispatching(true);
    try {
      const res = await fetch(`${API_URL}/orders/optimize-assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        throw new Error("Failed to optimize assignments");
      }

      const data = await res.json();
      await Promise.all([fetchOrders(), fetchAgents()]);
      alert(data.message);
    } catch (err) {
      alert(`Dispatch optimization failed: ${err.message}`);
    } finally {
      setIsDispatching(false);
    }
  };

  const stats = useMemo(() => {
    const activeOrders = orders.filter(
      (order) =>
        order.status !== "delivered" &&
        order.status !== "collected" &&
        order.status !== "cancelled",
    );
    const revenue = orders.reduce((sum, order) => sum + (order.total_amount || 0), 0);
    const availableAgents = agents.filter((agent) => agent.available);
    const unassignedOrders = orders.filter(
      (order) =>
        order.fulfillment_mode !== "takeaway" &&
        order.assignment_status === "unassigned" &&
        order.status !== "delivered" &&
        order.status !== "cancelled",
    );
    const activeDeliveryOrders = activeOrders.filter((order) => order.fulfillment_mode !== "takeaway");
    const activeTakeawayOrders = activeOrders.filter((order) => order.fulfillment_mode === "takeaway");

    return {
      activeOrders: activeOrders.length,
      revenue,
      availableAgents: availableAgents.length,
      unassignedOrders: unassignedOrders.length,
      activeDeliveryOrders: activeDeliveryOrders.length,
      activeTakeawayOrders: activeTakeawayOrders.length,
      busyAgents: agents.length - availableAgents.length,
      urgentOrders: activeOrders.filter((order) => order.priority === "urgent").length,
    };
  }, [agents, orders]);

  const routeInsights = useMemo(
    () =>
      agents
        .map((agent) => {
          const assignedOrders = orders.filter(
            (order) =>
              order.assigned_agent_id === agent.id &&
              order.fulfillment_mode !== "takeaway" &&
              order.status !== "delivered" &&
              order.status !== "cancelled",
          ).sort(sortRouteOrders);

          return {
            ...agent,
            assignedOrders,
            routeGroups: buildRouteGroups(assignedOrders),
          };
        })
        .filter((agent) => agent.assignedOrders.length > 0)
        .sort((left, right) => right.assignedOrders.length - left.assignedOrders.length),
    [agents, orders],
  );

  const activeTabMeta = tabs.find((tab) => tab.id === activeTab) || tabs[0];
  const selectTab = (tabId) => {
    setActiveTab(tabId);
    setIsSidebarOpen(false);
  };

  const renderActiveView = () => {
    if (activeTab === "menu") {
      return <OrderForm onOrderCreated={handleOrderCreated} onTrackOrder={handleTrackOrder} />;
    }

    if (activeTab === "kitchen") {
      return <KitchenDashboard orders={orders} onRefresh={fetchOrders} />;
    }

    if (activeTab === "orders") {
      return <OrderList orders={orders} onRefresh={fetchOrders} highlightedOrderId={highlightedOrderId} />;
    }

    if (activeTab === "agents") {
      return (
        <section className="space-y-6">
          <AgentForm onAgentCreated={handleAgentCreated} />
          <AgentList agents={agents} orders={orders} onRefresh={fetchAgents} />
        </section>
      );
    }

    if (activeTab === "map") {
      return (
        <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          <div className="overflow-hidden rounded-[32px] bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)] ring-1 ring-slate-200">
            <div className="border-b border-slate-200 px-6 py-5">
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-orange-600">Operations map</p>
              <h2 className="text-3xl font-black text-slate-950">Kitchen, orders, and riders in real time</h2>
            </div>
            <div className="map-shell">
              <MapContainer center={KITCHEN_LOCATION} zoom={12} className="h-full w-full">
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

                <Marker position={[KITCHEN_LOCATION.lat, KITCHEN_LOCATION.lng]}>
                  <Popup>Central kitchen</Popup>
                </Marker>

                {agents.map((agent) => (
                  <Marker key={agent.id} position={[agent.lat, agent.lng]}>
                    <Popup>
                      <div className="space-y-1">
                        <strong>{agent.name}</strong>
                        <p>Status: {agent.available ? "Available" : "Busy"}</p>
                        <p>Current load: {orders.filter((order) => order.assigned_agent_id === agent.id && order.status !== "delivered" && order.status !== "cancelled").length}</p>
                      </div>
                    </Popup>
                  </Marker>
                ))}

                {orders
                  .filter((order) => order.fulfillment_mode !== "takeaway" && order.status !== "cancelled")
                  .map((order) => (
                    <div key={order.id}>
                      <Marker position={[order.user_lat, order.user_lng]}>
                        <Popup>
                          <div className="space-y-1">
                            <strong>Order #{order.id.slice(-6)}</strong>
                            <p>{order.customer_name || "Guest"}</p>
                            <p>Mode: Delivery</p>
                            <p>Total: Rs. {(order.total_amount || 0).toFixed(2)}</p>
                            <p>Status: {order.status.replaceAll("_", " ")}</p>
                            {order.assigned_batch_size > 1 ? (
                              <p>Batch: {order.assigned_batch_size} drops | Batch stop {order.batch_stop_number}</p>
                            ) : null}
                            {order.route_stop_number ? <p>Route stop: {order.route_stop_number}</p> : null}
                            <p>ETA: {order.predicted_eta_minutes} min</p>
                          </div>
                        </Popup>
                      </Marker>
                      <Polyline
                        positions={[
                          [KITCHEN_LOCATION.lat, KITCHEN_LOCATION.lng],
                          [order.user_lat, order.user_lng],
                        ]}
                        color={
                          order.status === "delivered"
                            ? "#10b981"
                            : order.status === "in_transit"
                              ? "#0ea5e9"
                              : "#f97316"
                        }
                        weight={3}
                      />
                    </div>
                  ))}

                {orders
                  .filter(
                    (order) =>
                      order.fulfillment_mode === "takeaway" &&
                      order.status !== "cancelled" &&
                      order.status !== "collected",
                  )
                  .map((order, index) => (
                    <Marker
                      key={`pickup-${order.id}`}
                      position={[
                        KITCHEN_LOCATION.lat + 0.0035 + index * 0.0012,
                        KITCHEN_LOCATION.lng - 0.0035 + index * 0.0012,
                      ]}
                    >
                      <Popup>
                        <div className="space-y-1">
                          <strong>Pickup #{order.id.slice(-6)}</strong>
                          <p>{order.customer_name || "Guest"}</p>
                          <p>Mode: Takeaway</p>
                          <p>Status: {order.status.replaceAll("_", " ")}</p>
                          <p>Ready by: {formatDateTime(order.pickup_ready_at)}</p>
                          <p>Pickup from Cloud Kitchen Express</p>
                        </div>
                      </Popup>
                    </Marker>
                  ))}
              </MapContainer>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="rounded-[30px] bg-slate-950 p-6 text-white shadow-[0_18px_50px_rgba(15,23,42,0.18)]">
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-orange-200">Dispatch summary</p>
              <div className="mt-4 space-y-4 text-sm">
                <div className="rounded-2xl bg-white/10 p-4">
                  <p className="text-slate-300">Unassigned food orders</p>
                  <p className="mt-1 text-3xl font-black text-white">{stats.unassignedOrders}</p>
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  <p className="text-slate-300">Available riders</p>
                  <p className="mt-1 text-3xl font-black text-white">{stats.availableAgents}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-slate-300">Delivery orders</p>
                    <p className="mt-1 text-3xl font-black text-white">{stats.activeDeliveryOrders}</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-slate-300">Takeaway orders</p>
                    <p className="mt-1 text-3xl font-black text-white">{stats.activeTakeawayOrders}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-slate-300">Busy riders</p>
                    <p className="mt-1 text-3xl font-black text-white">{stats.busyAgents}</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-slate-300">Urgent orders</p>
                    <p className="mt-1 text-3xl font-black text-white">{stats.urgentOrders}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[30px] bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200">
              <h3 className="text-xl font-black text-slate-950">Dispatch routes</h3>
              <div className="mt-4 space-y-3">
                {routeInsights.length === 0 ? (
                  <div className="rounded-2xl bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                    No active rider routes yet. Run assignment once delivery orders are queued.
                  </div>
                ) : (
                  routeInsights.slice(0, 4).map((agent) => (
                    <div key={`route-${agent.id}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-slate-900">{agent.name}</p>
                            <span className="rounded-full bg-cyan-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-cyan-700">
                              {agent.assignedOrders.length} stops
                            </span>
                            <span className="rounded-full bg-orange-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-orange-700">
                              {agent.routeGroups.filter((group) => group.orders.length > 1).length} batches
                            </span>
                          </div>
                          <p className="text-sm text-slate-500">
                            {agent.routeGroups[0]?.orders.length > 1
                              ? `Next batch: ${agent.routeGroups[0].orders.length} nearby drops starting at ${agent.routeGroups[0].orders[0]?.delivery_area || "Direct drop"}`
                              : `Next drop: ${agent.assignedOrders[0]?.delivery_area || "Direct drop"}`}
                          </p>
                        </div>
                        <p className="text-sm font-bold text-slate-900">
                          Load {agent.assignedOrders.length}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </section>
      );
    }

    return null;
  };

  return (
    <div className="ck-app min-h-screen bg-[linear-gradient(180deg,#fff8ef_0%,#fffdf9_24%,#f8fafc_100%)] text-slate-900">
      {isSidebarOpen ? (
        <button
          type="button"
          aria-label="Close sidebar"
          className="ck-sidebar-backdrop fixed inset-0 z-40"
          onClick={() => setIsSidebarOpen(false)}
        />
      ) : null}

      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col">
        <aside
          className={`ck-sidebar fixed inset-y-0 left-0 z-50 flex w-[310px] max-w-[86vw] flex-col justify-between overflow-y-auto border-r border-orange-100 bg-[linear-gradient(180deg,#fff7ed_0%,#ffffff_38%,#fff1e6_100%)] px-6 py-7 transition-transform duration-300 ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}
        >
          <div>
            <button
              type="button"
              aria-label="Close sidebar"
              onClick={() => setIsSidebarOpen(false)}
              className="mb-4 ml-auto flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-xl font-black text-slate-700"
            >
              ×
            </button>

            <div className="ck-sidebar-card rounded-[30px] bg-white/90 p-5 shadow-[0_18px_40px_rgba(15,23,42,0.08)] ring-1 ring-orange-100">
              <div className="flex items-center gap-3">
                <img
                  src="/logo.png"
                  alt="Cloud Kitchen Express logo"
                  className="h-12 w-12 rounded-2xl object-cover ring-1 ring-orange-100"
                />
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-orange-600">
                    Cloud Kitchen OS
                  </p>
                  <p className="text-base font-black text-slate-950">Cloud Kitchen Express</p>
                </div>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-600">
                Production workspace for menu ordering, kitchen throughput, rider dispatch, and route visibility.
              </p>
            </div>

            <nav className="mt-6 space-y-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => selectTab(tab.id)}
                  className={`ck-nav-button w-full rounded-[24px] px-4 py-4 text-left transition ${activeTab === tab.id ? "is-active shadow-[0_16px_32px_rgba(15,23,42,0.22)]" : "hover:bg-white"
                    }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p
                      className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${activeTab === tab.id ? "text-slate-300" : "text-slate-400"
                        }`}
                    >
                      {tab.eyebrow}
                    </p>
                    <span className={`text-xs font-bold ${activeTab === tab.id ? "text-slate-400" : "text-slate-300"}`}>
                      {tab.shortcut}
                    </span>
                  </div>
                  <p className="mt-2 text-base font-black">{tab.label}</p>
                  <p className={`mt-1 text-sm ${activeTab === tab.id ? "text-slate-300" : "text-slate-500"}`}>
                    {tab.title}
                  </p>
                </button>
              ))}
            </nav>
          </div>

          <div className="space-y-4">
            <div className="rounded-[24px] bg-white p-4 text-sm shadow-sm ring-1 ring-slate-200 md:hidden">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Signed in</p>
              <p className="mt-2 font-bold text-slate-900">{currentUser?.role_display || "Admin"}</p>
              <p className="text-slate-500">{currentUser?.email || "Operations user"}</p>
              <button
                type="button"
                onClick={onLogout}
                className="mt-3 w-full rounded-full bg-slate-950 px-4 py-2 text-sm font-bold text-white"
              >
                Sign out
              </button>
            </div>

            <button
              type="button"
              onClick={optimizeAssignments}
              disabled={isDispatching}
              className="ck-command-button w-full rounded-[24px] bg-orange-500 px-5 py-4 text-sm font-bold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isDispatching ? "Optimizing dispatch..." : "Optimize dispatch"}
            </button>

            <div className="rounded-[28px] bg-slate-950 p-5 text-white shadow-[0_18px_40px_rgba(15,23,42,0.22)]">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-200">Live overview</p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                {statCards(stats).map((card) => (
                  <div
                    key={card.label}
                    className={`ck-stat-card rounded-2xl p-3 ${card.tone === "dark" ? "bg-orange-500 text-white" : "bg-white/10 text-white"
                      }`}
                  >
                    <p className={`text-[11px] uppercase tracking-[0.18em] ${card.tone === "dark" ? "text-orange-50" : "text-slate-300"}`}>
                      {card.label}
                    </p>
                    <p className="mt-2 text-2xl font-black">{card.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-orange-100 bg-[radial-gradient(circle_at_top_left,_rgba(251,146,60,0.18),_transparent_24%),linear-gradient(135deg,#fffaf3_0%,#ffffff_44%,#eff6ff_100%)]">
            <div className="px-4 py-5 md:px-6 xl:px-8">
              <div className="flex flex-col gap-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        aria-label="Open sidebar"
                        aria-expanded={isSidebarOpen}
                        onClick={() => setIsSidebarOpen(true)}
                        className="ck-menu-button flex h-11 w-11 shrink-0 flex-col items-center justify-center gap-1.5 rounded-2xl border border-slate-200 bg-white"
                      >
                        <span />
                        <span />
                        <span />
                      </button>
                      <img
                        src="/logo.png"
                        alt="Cloud Kitchen Express logo"
                        className="h-11 w-11 rounded-2xl object-cover ring-1 ring-orange-100"
                      />
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-orange-600">
                          Cloud Kitchen OS
                        </p>
                        <p className="text-sm font-black text-slate-950">Cloud Kitchen Express</p>
                      </div>
                    </div>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-[0.24em] text-orange-600">
                      {activeTabMeta.eyebrow}
                    </p>
                    <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-5xl">
                      {activeTabMeta.title}
                    </h1>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 md:text-base">
                      {activeTabMeta.description}
                    </p>
                  </div>

                  <div className="hidden shrink-0 items-center gap-3 md:flex">
                    <div className="rounded-full bg-white px-4 py-2 text-right text-xs shadow-sm ring-1 ring-slate-200">
                      <p className="font-bold text-slate-900">{currentUser?.role_display || "Admin"}</p>
                      <p className="text-slate-500">{currentUser?.email || "Signed in"}</p>
                    </div>
                    <button
                      type="button"
                      onClick={optimizeAssignments}
                      disabled={isDispatching}
                      className="ck-command-button rounded-full bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isDispatching ? "Optimizing dispatch..." : "Optimize dispatch"}
                    </button>
                    <button
                      type="button"
                      onClick={onLogout}
                      className="rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-800"
                    >
                      Sign out
                    </button>
                  </div>
                </div>

                <nav className="xl:hidden">
                  <div className="ck-mobile-tabbar flex gap-3 overflow-x-auto pb-1">
                    {tabs.map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => selectTab(tab.id)}
                        className={`shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition ${activeTab === tab.id
                            ? "bg-slate-950 text-white shadow-lg"
                            : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
                          }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </nav>

                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {statCards(stats).map((card) => (
                    <div
                      key={card.label}
                      className={`ck-stat-card rounded-[24px] px-4 py-4 shadow-sm ring-1 ${card.tone === "dark"
                          ? "bg-slate-950 text-white ring-slate-950"
                          : "bg-white text-slate-900 ring-orange-100"
                        }`}
                    >
                      <p
                        className={`text-xs uppercase tracking-[0.18em] ${card.tone === "dark" ? "text-orange-200" : "text-slate-500"
                          }`}
                      >
                        {card.label}
                      </p>
                      <p className="mt-2 text-2xl font-black">{card.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-8 md:px-6 xl:px-8">{renderActiveView()}</main>
        </div>
      </div>
    </div>
  );
}

