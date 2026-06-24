import { useCallback, useEffect, useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AdminDashboard from "./components/AdminDashboard";
import LoginPage from "./components/LoginPage";
import OrderForm from "./components/OrderForm";
import { API_BASE_URL, API_URL, TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from "./config/api";

const originalFetch = window.fetch.bind(window);
const allowedApiOrigins = new Set([
  API_BASE_URL,
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);
const legacyRoleMap = {
  admin: "super_admin",
  manager: "branch_manager",
  delivery: "delivery_agent",
  agent: "delivery_agent",
};

const normalizeRole = (role) => legacyRoleMap[role] || role;

window.fetch = async (resource, config = {}) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!token) {
    return originalFetch(resource, config);
  }

  const requestUrl = typeof resource === "string" ? resource : resource?.url;
  const shouldAttachToken = [...allowedApiOrigins].some((origin) => requestUrl?.startsWith(origin));
  if (!shouldAttachToken) {
    return originalFetch(resource, config);
  }

  const headers = new Headers(config.headers || (resource instanceof Request ? resource.headers : undefined));
  headers.set("Authorization", `Bearer ${token}`);

  if (resource instanceof Request) {
    return originalFetch(new Request(resource, { ...config, headers }));
  }

  return originalFetch(resource, { ...config, headers });
};

function LoadingScreen() {
  return (
    <div className="ck-app flex min-h-screen items-center justify-center px-4">
      <div className="rounded-[28px] bg-white px-8 py-7 text-center shadow-[0_24px_60px_rgba(15,23,42,0.12)] ring-1 ring-orange-100">
        <img src="/logo.png" alt="Cloud Kitchen Express logo" className="mx-auto h-14 w-14 rounded-2xl object-cover" />
        <p className="mt-4 text-sm font-semibold uppercase tracking-[0.2em] text-orange-600">Checking session</p>
        <p className="mt-2 text-sm text-slate-500">Preparing your workspace...</p>
      </div>
    </div>
  );
}

function RoleHome({ currentUser, onLogout }) {
  return (
    <div className="ck-app min-h-screen px-4 py-8">
      <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-4xl items-center">
        <section className="w-full rounded-[32px] bg-white p-8 shadow-[0_24px_60px_rgba(15,23,42,0.12)] ring-1 ring-orange-100">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-600">
                Signed in
              </p>
              <h1 className="mt-3 text-4xl font-black text-slate-950">Welcome, {currentUser?.name || currentUser?.email || "team member"}.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                Your account is active as {currentUser?.role_display || currentUser?.role}. Role-specific dashboards can attach here next without changing the admin portal.
              </p>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white"
            >
              Sign out
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

const formatDateTime = (value) => (value ? new Date(value).toLocaleString() : "Not available");
const formatPrice = (value) => `Rs. ${(value || 0).toFixed(2)}`;

function CustomerProfilePanel({ currentUser, onClose, onLogout }) {
  const [orders, setOrders] = useState([]);
  const [loadingOrders, setLoadingOrders] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchOrders = async () => {
      setLoadingOrders(true);
      setError("");
      try {
        const res = await fetch(`${API_URL}/orders/`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.message || "Failed to load order history");
        setOrders(data.orders || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingOrders(false);
      }
    };

    void fetchOrders();
  }, []);

  return (
    <div className="fixed inset-0 z-[70] bg-slate-950/45 px-4 py-6 backdrop-blur-sm">
      <aside className="ml-auto flex h-full w-full max-w-xl flex-col overflow-hidden rounded-[30px] bg-white shadow-[0_28px_80px_rgba(15,23,42,0.3)]">
        <div className="bg-slate-950 p-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-200">Your profile</p>
              <h2 className="mt-2 text-2xl font-black text-white">{currentUser?.name || "Customer"}</h2>
              <p className="mt-1 text-sm text-slate-300">{currentUser?.email || currentUser?.phone || "Verified customer"}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-xl font-black text-white"
              aria-label="Close profile"
            >
              x
            </button>
          </div>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          <section className="rounded-[24px] bg-orange-50 p-4 ring-1 ring-orange-100">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-orange-600">Personal details</p>
            <div className="mt-4 grid gap-3 text-sm text-slate-700">
              <p>Name: <span className="font-semibold text-slate-950">{currentUser?.name || "Not provided"}</span></p>
              <p>Email: <span className="font-semibold text-slate-950">{currentUser?.email || "Not provided"}</span></p>
              <p>Phone: <span className="font-semibold text-slate-950">{currentUser?.phone || "Not provided"}</span></p>
              <p>Account type: <span className="font-semibold text-slate-950">{currentUser?.role_display || "Customer"}</span></p>
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-orange-600">Order history</p>
                <h3 className="mt-1 text-xl font-black text-slate-950">{orders.length} orders</h3>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {loadingOrders ? (
                <div className="rounded-[24px] bg-slate-50 px-5 py-8 text-center text-sm text-slate-500">
                  Loading your orders...
                </div>
              ) : error ? (
                <div className="rounded-[24px] bg-rose-50 px-5 py-4 text-sm font-semibold text-rose-700 ring-1 ring-rose-100">
                  {error}
                </div>
              ) : orders.length === 0 ? (
                <div className="rounded-[24px] bg-slate-50 px-5 py-8 text-center text-sm text-slate-500">
                  No orders yet. Your completed and live orders will appear here.
                </div>
              ) : (
                orders.map((order) => (
                  <article key={order.id} className="rounded-[24px] bg-slate-50 p-4 ring-1 ring-slate-200">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-black text-slate-950">Order #{order.id.slice(-6)}</p>
                        <p className="mt-1 text-xs text-slate-500">{formatDateTime(order.created_at)}</p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-bold capitalize text-slate-700 ring-1 ring-slate-200">
                        {order.status?.replaceAll("_", " ")}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(order.items || []).slice(0, 3).map((item) => (
                        <span key={`${order.id}-${item.dish_id}`} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                          {item.name} x{item.quantity}
                        </span>
                      ))}
                    </div>
                    <div className="mt-4 flex items-center justify-between text-sm">
                      <span className="text-slate-500">{order.fulfillment_mode === "takeaway" ? "Pickup" : order.delivery_area || "Delivery"}</span>
                      <span className="font-black text-slate-950">{formatPrice(order.total_amount)}</span>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>

        <div className="border-t border-slate-200 p-5">
          <button
            type="button"
            onClick={onLogout}
            className="w-full rounded-2xl bg-slate-950 px-5 py-3 text-sm font-bold text-white"
          >
            Logout
          </button>
        </div>
      </aside>
    </div>
  );
}

function PublicMenu({ currentUser, onCustomerAuth, onLogout }) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const navigate = useNavigate();
  const requireCustomerLogin = () => navigate("/gmail-login");

  return (
    <div className="ck-app min-h-screen bg-[linear-gradient(180deg,#fff8ef_0%,#fffdf9_24%,#f8fafc_100%)] px-4 py-8">
      <OrderForm
        currentUser={currentUser}
        onCustomerAuth={onCustomerAuth}
        onProfileClick={() => setIsProfileOpen(true)}
        onLoginRequired={requireCustomerLogin}
        onOrderCreated={() => { }}
        onTrackOrder={() => { }}
      />

      {isProfileOpen ? (
        <CustomerProfilePanel
          currentUser={currentUser}
          onClose={() => setIsProfileOpen(false)}
          onLogout={() => {
            setIsProfileOpen(false);
            onLogout();
          }}
        />
      ) : null}
    </div>
  );
}

function GmailLoginPage({ currentUser, onCustomerAuth }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", name: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (currentUser?.role === "customer") {
    return <Navigate to="/menu" replace />;
  }

  const handleChange = ({ target: { name, value } }) => {
    setForm((current) => ({ ...current, [name]: value }));
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const res = await originalFetch(`${API_BASE_URL}/auth/gmail/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          data.detail === "Service temporarily unavailable. Please try again."
            ? "Customer login is waiting for the database connection. Please try again once MongoDB is healthy."
            : data.detail || "Gmail login failed",
        );
      }
      onCustomerAuth(data);
      navigate("/menu", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="ck-app min-h-screen bg-[linear-gradient(180deg,#fff8ef_0%,#fffdf9_35%,#f8fafc_100%)] px-4 py-8">
      <main className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-5xl items-center gap-8 lg:grid-cols-[1fr_420px]">
        <section>
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Cloud Kitchen Express logo" className="h-14 w-14 rounded-2xl object-cover ring-1 ring-orange-100" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-orange-600">Cloud Kitchen OS</p>
              <p className="text-lg font-black text-slate-950">Cloud Kitchen Express</p>
            </div>
          </div>
          <h1 className="mt-8 max-w-2xl text-4xl font-black tracking-tight text-slate-950 md:text-6xl">
            Sign in with Gmail before you order.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
            Browse the menu freely. Your cart and checkout are connected to your customer account so order history and profile details stay in one place.
          </p>
        </section>

        <section className="rounded-[30px] bg-white p-6 shadow-[0_24px_60px_rgba(15,23,42,0.12)] ring-1 ring-orange-100">
          <div className="rounded-[24px] bg-slate-950 px-5 py-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-200">Customer login</p>
            <h2 className="mt-2 text-2xl font-black text-white">Continue with Gmail</h2>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Gmail address
              </span>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@gmail.com"
                required
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Name
              </span>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="Your name"
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none"
              />
            </label>

            {error ? (
              <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 ring-1 ring-rose-100">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting}
              className="ck-command-button w-full rounded-2xl px-5 py-4 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Signing in..." : "Continue"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/menu")}
              className="w-full rounded-2xl bg-slate-100 px-5 py-3 text-sm font-bold text-slate-700"
            >
              Back to menu
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}

function ProtectedRoute({ currentUser, loading, requireAdmin = false, children }) {
  const location = useLocation();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!currentUser) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requireAdmin && currentUser.role !== "super_admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppRoutes({ currentUser, loading, login, logout, onCustomerAuth }) {
  const landingPath = useMemo(() => {
    if (!currentUser) return "/menu";
    return currentUser.role === "super_admin" ? "/admin" : "/dashboard";
  }, [currentUser]);

  return (
    <Routes>
      <Route path="/" element={<PublicMenu currentUser={currentUser} onCustomerAuth={onCustomerAuth} onLogout={logout} />} />
      <Route path="/menu" element={<PublicMenu currentUser={currentUser} onCustomerAuth={onCustomerAuth} onLogout={logout} />} />
      <Route path="/gmail-login" element={<GmailLoginPage currentUser={currentUser} onCustomerAuth={onCustomerAuth} />} />
      <Route path="/login" element={<LoginPage currentUser={currentUser} onLogin={login} />} />
      <Route path="/ops-login" element={<LoginPage mode="admin" currentUser={currentUser} onLogin={login} />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute currentUser={currentUser} loading={loading}>
            <RoleHome currentUser={currentUser} onLogout={logout} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute currentUser={currentUser} loading={loading} requireAdmin>
            <AdminDashboard currentUser={currentUser} onLogout={logout} />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to={landingPath} replace />} />
    </Routes>
  );
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem(USER_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(TOKEN_STORAGE_KEY)));

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setCurrentUser(null);
  }, []);

  const persistUser = useCallback((user) => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    setCurrentUser(user);
  }, []);

  const refreshCurrentUser = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const res = await originalFetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Session expired");
      const user = await res.json();
      persistUser({ ...user, role: normalizeRole(user.role) });
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  }, [logout, persistUser]);

  useEffect(() => {
    void refreshCurrentUser();
  }, [refreshCurrentUser]);

  const login = useCallback(
    async ({ email, password }, { adminOnly = false } = {}) => {
      const res = await originalFetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        throw new Error("Invalid email or password.");
      }

      const auth = await res.json();
      const role = normalizeRole(auth.role);
      if (adminOnly && role !== "super_admin") {
        throw new Error("This portal is only for super admin accounts.");
      }
      if (!adminOnly && role === "super_admin") {
        throw new Error("Super admin accounts use the operations access route.");
      }

      const user = {
        user_id: auth.user_id,
        email,
        role,
        role_display: auth.role_display,
        branch_id: auth.branch_id,
      };

      localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
      persistUser(user);
      return user;
    },
    [persistUser],
  );

  const authenticateCustomer = useCallback(
    (auth) => {
      const role = normalizeRole(auth.role);
      const user = {
        user_id: auth.user_id,
        email: auth.email || "",
        name: auth.name || "",
        phone: auth.phone || "",
        role,
        role_display: auth.role_display,
        branch_id: auth.branch_id,
      };

      localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
      persistUser(user);
      return user;
    },
    [persistUser],
  );

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <BrowserRouter>
      <AppRoutes currentUser={currentUser} loading={loading} login={login} logout={logout} onCustomerAuth={authenticateCustomer} />
    </BrowserRouter>
  );
}
