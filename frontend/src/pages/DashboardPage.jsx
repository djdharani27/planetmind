import { useState, useEffect } from "react";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);

  const fetchStats = () => {
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
    fetch("/api/pipeline/jobs")
      .then((r) => r.json())
      .then(setJobs)
      .catch(() => {});
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
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

  const metrics = [
    { label: "Total Documents", value: stats.total_documents, color: "text-white" },
    { label: "Ready for Search", value: stats.documents_ready, color: "text-green-400" },
    { label: "Processing", value: stats.documents_processing, color: "text-yellow-400" },
    { label: "Failed", value: stats.documents_failed, color: "text-red-400" },
    { label: "Graph Nodes", value: stats.graph_nodes, color: "text-purple-400" },
    { label: "Graph Relationships", value: stats.graph_relationships, color: "text-pink-400" },
    { label: "Vectors (Qdrant)", value: stats.vector_count, color: "text-cyan-400" },
    { label: "Success Rate", value: `${stats.processing_success_rate}%`, color: "text-blue-400" },
  ];

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl md:text-3xl font-bold mb-2">Dashboard</h1>
      <p className="text-gray-400 mb-8 text-sm md:text-base">Processing overview and statistics</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-500 text-xs mb-1">{m.label}</p>
            <p className={`text-2xl font-bold ${m.color}`}>{m.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-bold mb-3">Processing Pipeline</h2>
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="space-y-2">
              {Object.entries(stats.by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center gap-3">
                  <span className={`w-3 h-3 rounded-full ${statusColors[status] || "bg-gray-600"}`} />
                  <span className="flex-1 capitalize text-sm">{status.replace(/_/g, " ")}</span>
                  <span className="text-gray-400 text-sm">{count}</span>
                </div>
              ))}
              {Object.keys(stats.by_status || {}).length === 0 && (
                <p className="text-gray-500 text-sm">No documents yet</p>
              )}
            </div>
          </div>
        </div>

        <div>
          <h2 className="text-lg font-bold mb-3">Live Jobs</h2>
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            {jobs.length === 0 && <p className="text-gray-500 text-sm">No active jobs</p>}
            {jobs.map((job) => (
              <div key={job.job_id} className="mb-3 border-b border-gray-800 pb-3 last:border-0 last:pb-0">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium font-mono">{job.job_id.slice(-12)}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    job.status === "running" ? "bg-yellow-600" : 
                    job.status === "completed" ? "bg-green-600" : "bg-red-600"
                  }`}>{job.status}</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2 mb-1">
                  <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${job.progress}%` }} />
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(job.steps || {}).map(([step, status]) => (
                    <span key={step} className="text-xs bg-gray-800 px-1.5 py-0.5 rounded">{step}: {status}</span>
                  ))}
                </div>
                {job.error && <p className="text-red-400 text-xs mt-1">{job.error}</p>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
