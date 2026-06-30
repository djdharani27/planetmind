import { useState } from "react";
import { apiFetch } from "../lib/api";

export default function MaintenancePage() {
  const [query, setQuery] = useState("");
  const [equipmentId, setEquipmentId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("rca");

  const analyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const endpoint = mode === "rca" ? "/maintenance/rca" : "/maintenance/predict";
      const data = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ query, equipment_id: equipmentId || null, top_k: 15 }),
      });
      setResult(data);
    } catch {
      setResult({ error: "Analysis failed" });
    }
    setLoading(false);
  };

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl md:text-3xl font-bold mb-2">Maintenance Intelligence & RCA</h1>
      <p className="text-gray-400 mb-6 text-sm md:text-base">Root Cause Analysis and predictive maintenance recommendations</p>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setMode("rca")} className={`px-4 py-2 rounded-lg text-sm ${mode === "rca" ? "bg-blue-600" : "bg-gray-800"}`}>RCA</button>
        <button onClick={() => setMode("predict")} className={`px-4 py-2 rounded-lg text-sm ${mode === "predict" ? "bg-blue-600" : "bg-gray-800"}`}>Predictive</button>
      </div>

      <div className="flex flex-col md:flex-row gap-2 mb-6">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder='e.g. "Pump P-204 bearing failure analysis"' className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm" />
        <input value={equipmentId} onChange={(e) => setEquipmentId(e.target.value)} placeholder="Equipment ID (optional)" className="md:w-48 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm" />
        <button onClick={analyze} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-lg text-sm font-medium whitespace-nowrap">
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          {result.error && <p className="text-red-400 bg-red-900/30 rounded-lg p-4">{result.error}</p>}
          {result.root_causes && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-red-400">Root Causes</h3>
              {result.root_causes.map((rc, i) => (
                <div key={i} className="mb-2 text-sm">
                  <span className="font-medium">{rc.cause}</span>
                  <p className="text-gray-400 text-xs">{rc.evidence}</p>
                  <span className="text-xs bg-gray-800 px-1.5 py-0.5 rounded">Confidence: {(rc.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}
          {result.predictive_recommendations && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-green-400">Recommendations</h3>
              {result.predictive_recommendations.map((r, i) => (
                <div key={i} className="mb-2 text-sm border-b border-gray-800 pb-2">
                  <p className="font-medium">{r.action}</p>
                  <p className="text-gray-400 text-xs">Interval: {r.interval_days} days | {r.justification}</p>
                </div>
              ))}
            </div>
          )}
          {result.failure_patterns && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-yellow-400">Failure Patterns</h3>
              {result.failure_patterns.map((fp, i) => (
                <p key={i} className="text-sm text-gray-300 mb-1">{fp.pattern || fp.source}</p>
              ))}
            </div>
          )}
          {result.overall_confidence !== undefined && (
            <p className="text-right text-sm text-gray-500">Overall confidence: {(result.overall_confidence * 100).toFixed(0)}%</p>
          )}
        </div>
      )}
    </div>
  );
}
