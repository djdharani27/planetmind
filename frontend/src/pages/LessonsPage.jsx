import { useState } from "react";

export default function LessonsPage() {
  const [query, setQuery] = useState("");
  const [equipmentType, setEquipmentType] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("analyze");

  const analyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const endpoint = mode === "analyze" ? "/api/lessons/analyze" : "/api/lessons/warnings";
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, equipment_type: equipmentType || null, top_k: 15 }),
      });
      setResult(await res.json());
    } catch {
      setResult({ error: "Analysis failed" });
    }
    setLoading(false);
  };

  const urgencyColor = (u) =>
    ({ immediate: "text-red-400 bg-red-900/20 border-red-700", soon: "text-yellow-400 bg-yellow-900/20 border-yellow-700", informational: "text-blue-400 bg-blue-900/20 border-blue-700" })[u] || "text-gray-400";

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl md:text-3xl font-bold mb-2">Lessons Learned & Failure Intelligence</h1>
      <p className="text-gray-400 mb-6 text-sm md:text-base">Systemic pattern detection, proactive warnings, and cross-referenced failure analysis</p>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setMode("analyze")} className={`px-4 py-2 rounded-lg text-sm ${mode === "analyze" ? "bg-blue-600" : "bg-gray-800"}`}>Pattern Analysis</button>
        <button onClick={() => setMode("warnings")} className={`px-4 py-2 rounded-lg text-sm ${mode === "warnings" ? "bg-blue-600" : "bg-gray-800"}`}>Proactive Warnings</button>
      </div>

      <div className="flex flex-col md:flex-row gap-2 mb-6">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder='e.g. "Bearing failure incidents across all pumps"' className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm" />
        <input value={equipmentType} onChange={(e) => setEquipmentType(e.target.value)} placeholder="Equipment type (e.g. Pumps)" className="md:w-48 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm" />
        <button onClick={analyze} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-lg text-sm font-medium whitespace-nowrap">
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          {result.error && <p className="text-red-400 bg-red-900/30 rounded-lg p-4">{result.error}</p>}
          {result.proactive_warnings && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-yellow-400">⚠ Proactive Warnings</h3>
              {result.proactive_warnings.map((w, i) => (
                <div key={i} className={`mb-2 p-3 rounded-lg border text-sm ${urgencyColor(w.urgency)}`}>
                  <p className="font-medium">{w.warning}</p>
                  <p className="text-xs mt-1">Target: {w.target_team} | Urgency: {w.urgency}</p>
                </div>
              ))}
            </div>
          )}
          {result.identified_patterns && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-purple-400">Systemic Patterns</h3>
              {result.identified_patterns.map((p, i) => (
                <div key={i} className="mb-2 text-sm border-b border-gray-800 pb-2">
                  <p className="font-medium">{p.pattern}</p>
                  <p className="text-gray-400 text-xs">Occurrences: {p.occurrences} | {p.first_seen} – {p.last_seen}</p>
                </div>
              ))}
            </div>
          )}
          {result.systemic_risks && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-red-400">Systemic Risks</h3>
              {result.systemic_risks.map((r, i) => (
                <div key={i} className="mb-2 text-sm">
                  <span className="font-medium">{r.risk}</span>
                  <div className="flex gap-2 mt-1">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${r.probability === "high" ? "bg-red-900/40 text-red-300" : "bg-yellow-900/40 text-yellow-300"}`}>{r.probability}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${r.impact === "critical" ? "bg-red-900/40 text-red-300" : "bg-orange-900/40 text-orange-300"}`}>{r.impact}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          {result.lessons_learned && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-green-400">Lessons Learned</h3>
              {result.lessons_learned.map((l, i) => (
                <div key={i} className="mb-2 text-sm border-b border-gray-800 pb-2">
                  <p>{l.lesson}</p>
                  <p className="text-gray-400 text-xs">Source: {l.source_incident} | Applicable: {l.applicable_equipment?.join(", ")}</p>
                </div>
              ))}
            </div>
          )}
          {result.overall_risk_score !== undefined && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <span className="text-2xl font-bold text-red-400">{(result.overall_risk_score * 100).toFixed(0)}%</span>
              <p className="text-xs text-gray-500">Overall Risk Score</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
