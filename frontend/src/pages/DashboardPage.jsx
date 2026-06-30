import { useState, useEffect } from "react";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  if (!stats) return <div className="p-8 text-gray-400">Loading...</div>;

  const statusColors = {
    uploaded: "bg-blue-600",
    processing: "bg-yellow-500",
    ocr_complete: "bg-purple-500",
    parsing_complete: "bg-indigo-500",
    chunking_complete: "bg-teal-500",
    embeddings_complete: "bg-cyan-500",
    entities_complete: "bg-orange-500",
    graph_complete: "bg-pink-500",
    ready: "bg-green-500",
    failed: "bg-red-500",
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
      <p className="text-gray-400 mb-8">Processing overview and statistics</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <p className="text-gray-400 text-sm">Total Documents</p>
          <p className="text-4xl font-bold mt-1">{stats.total_documents}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <p className="text-gray-400 text-sm">Ready for Search</p>
          <p className="text-4xl font-bold mt-1 text-green-400">{stats.by_status?.ready || 0}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <p className="text-gray-400 text-sm">Processing</p>
          <p className="text-4xl font-bold mt-1 text-yellow-400">{stats.by_status?.processing || 0}</p>
        </div>
      </div>

      <h2 className="text-xl font-bold mb-4">Processing Pipeline</h2>
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <div className="space-y-2">
          {Object.entries(stats.by_status || {}).map(([status, count]) => (
            <div key={status} className="flex items-center gap-3">
              <span className={`w-3 h-3 rounded-full ${statusColors[status] || "bg-gray-600"}`} />
              <span className="flex-1 capitalize text-sm">{status.replace(/_/g, " ")}</span>
              <span className="text-gray-400 text-sm">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
