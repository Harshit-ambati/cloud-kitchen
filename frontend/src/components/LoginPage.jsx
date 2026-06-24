import { useState } from "react";
import { Navigate } from "react-router-dom";

function RoleBadge({ children }) {
  return (
    <span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-orange-600 ring-1 ring-orange-100">
      {children}
    </span>
  );
}

export default function LoginPage({ mode = "standard", currentUser, onLogin }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isAdminPortal = mode === "admin";

  if (currentUser) {
    if (currentUser.role === "super_admin") {
      return <Navigate to="/admin" replace />;
    }
    return <Navigate to="/dashboard" replace />;
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
      const user = await onLogin(form, { adminOnly: isAdminPortal });
      if (!isAdminPortal && user.role === "super_admin") {
        setError("Super admin accounts use the operations access route.");
      }
    } catch (err) {
      setError(err.message || "Login failed. Please check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="ck-app min-h-screen bg-[linear-gradient(180deg,#fff8ef_0%,#fffdf9_35%,#f8fafc_100%)] px-4 py-8 text-slate-900">
      <main className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_420px]">
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <img
              src="/logo.png"
              alt="Cloud Kitchen Express logo"
              className="h-14 w-14 rounded-2xl object-cover ring-1 ring-orange-100"
            />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-orange-600">
                Cloud Kitchen OS
              </p>
              <p className="text-lg font-black text-slate-950">Cloud Kitchen Express</p>
            </div>
          </div>

          <div className="max-w-2xl">
            <RoleBadge>{isAdminPortal ? "Operations access" : "Secure sign in"}</RoleBadge>
            <h1 className="mt-5 text-4xl font-black tracking-tight text-slate-950 md:text-6xl">
              {isAdminPortal ? "Admin control stays behind its own door." : "Sign in to your kitchen workspace."}
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
              {isAdminPortal
                ? "This route is reserved for super admin accounts and is not linked from the public dashboard."
                : "Use your assigned account to continue into the cloud kitchen system."}
            </p>
          </div>

          <div className="grid max-w-2xl gap-3 sm:grid-cols-3">
            {["Orders", "Kitchen", "Dispatch"].map((label) => (
              <div key={label} className="rounded-[24px] bg-white px-4 py-4 shadow-sm ring-1 ring-orange-100">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">Protected</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[30px] bg-white p-6 shadow-[0_24px_60px_rgba(15,23,42,0.12)] ring-1 ring-orange-100">
          <div className="rounded-[24px] bg-slate-950 px-5 py-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-200">
              {isAdminPortal ? "Admin portal" : "Account login"}
            </p>
            <h2 className="mt-2 text-2xl font-black text-white">
              {isAdminPortal ? "Super admin sign in" : "Welcome back"}
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Email or username
              </span>
              <input
                type="text"
                name="email"
                value={form.email}
                onChange={handleChange}
                autoComplete="username"
                required
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Password
              </span>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                autoComplete={isAdminPortal ? "current-password" : "current-password"}
                required
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
              {isSubmitting ? "Signing in..." : isAdminPortal ? "Enter admin dashboard" : "Sign in"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
