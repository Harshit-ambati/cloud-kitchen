const API_URL = "http://localhost:8000/api";

export default function AgentList({ agents, onRefresh }) {
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
      {agents.map((agent) => (
        <div
          key={agent.id}
          className="rounded-lg border border-gray-200 bg-white p-4 transition hover:shadow-lg"
        >
          <div className="mb-3 flex items-start justify-between">
            <div>
              <h3 className="font-bold text-gray-900">{agent.name}</h3>
              <p className="text-xs text-gray-500">ID: {agent.id.slice(-8)}</p>
            </div>
            <span
              className={`rounded-full px-2 py-1 text-xs font-semibold ${
                agent.available ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"
              }`}
            >
              {agent.status}
            </span>
          </div>

          <div className="mb-4 space-y-2 text-sm text-gray-600">
            <p>
              Lat: <strong>{agent.lat.toFixed(4)}</strong>
            </p>
            <p>
              Lng: <strong>{agent.lng.toFixed(4)}</strong>
            </p>
            <p>
              Active Load: <strong>{agent.current_load || 0}</strong>
            </p>
            <p>
              Deliveries: <strong>{agent.total_deliveries || 0}</strong>
            </p>
            <p>
              Rating: <strong>{agent.avg_rating?.toFixed(1) || "5.0"}/5</strong>
            </p>
          </div>

          <button
            onClick={() => handleDelete(agent.id)}
            className="w-full rounded-lg bg-red-100 py-2 text-sm font-medium text-red-700 hover:bg-red-200"
          >
            Delete Agent
          </button>
        </div>
      ))}
    </div>
  );
}
