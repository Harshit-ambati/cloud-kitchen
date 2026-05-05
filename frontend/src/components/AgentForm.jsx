import { useState } from "react";

const API_URL = "http://localhost:8000/api";

export default function AgentForm({ onAgentCreated }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    lat: 17.385,
    lng: 78.4867,
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "name" ? value : parseFloat(value),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/agents/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        throw new Error("Failed to create agent");
      }

      const data = await res.json();
      onAgentCreated(data);
      setFormData({ name: "", lat: 17.385, lng: 78.4867 });
      alert(`Agent ${data.name} created.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-5 rounded-[28px] bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] ring-1 ring-slate-200 lg:grid-cols-[1fr_1.4fr_auto] lg:items-end"
    >
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Fleet onboarding</p>
        <h3 className="mt-2 text-xl font-black text-slate-950">Add delivery rider</h3>
        <p className="mt-1 text-sm text-slate-500">
          Register rider coordinates so dispatch can include them in assignment planning.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-slate-700">Rider name</span>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="Aarav Sharma"
            className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            required
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-slate-700">Latitude</span>
          <input
            type="number"
            name="lat"
            step="0.0001"
            value={formData.lat}
            onChange={handleChange}
            className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            required
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-slate-700">Longitude</span>
          <input
            type="number"
            name="lng"
            step="0.0001"
            value={formData.lng}
            onChange={handleChange}
            className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            required
          />
        </label>
      </div>

      {error && <p className="text-sm font-medium text-rose-600 lg:col-span-3">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Creating..." : "Create Agent"}
      </button>
    </form>
  );
}
