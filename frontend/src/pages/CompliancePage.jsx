import { useState } from "react";

export default function CompliancePage() {
  const [query, setQuery] = useState("");
  const [regulation, setRegulation] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("analyze");

  const analyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const endpoint = mode === "analyze" ? "/api/compliance/analyze" : "/api/compliance/audit";
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, regulation: regulation || null, top_k: 15 }),
      });
      setResult(await res.json());
    } catch {
      setResult({ error: "Analysis failed" });
    }
    setLoading(false);
  };

  const severityColor = (s) =>
    ({ critical: "text-red-400 bg-red-900/20", high: "text-orange-400 bg-orange-900/20", medium: "text-yellow-400 bg-yellow-900/20", low: "text-green-400 bg-green-900/20" })[s] || "text-gray-400";

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl md:text-3xl font-bold mb-2">Quality & Regulatory Compliance</h1>
      <p className="text-gray-400 mb-6 text-sm md:text-base">Factory Act, OISD, PESO, ISO compliance analysis and audit preparation</p>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setMode("analyze")} className={`px-4 py-2 rounded-lg text-sm ${mode === "analyze" ? "bg-blue-600" : "bg-gray-800"}`}>Gap Analysis</button>
        <button onClick={() => setMode("audit")} className={`px-4 py-2 rounded-lg text-sm ${mode === "audit" ? "bg-blue-600" : "bg-gray-800"}`}>Audit Package</button>
      </div>

      <div className="flex flex-col md:flex-row gap-2 mb-6">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder='e.g. "Factory Act inspection compliance for turbine area"' className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm" />
        <input value={regulation} onChange={(e) => setRegulation(e.target.value)} placeholder="Regulation (e.g. OISD, PESO)" className="md:w-48 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm" />
        <button onClick={analyze} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-lg text-sm font-medium whitespace-nowrap">
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          {result.error && <p className="text-red-400 bg-red-900/30 rounded-lg p-4">{result.error}</p>}
          {result.applicable_regulations && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2">Applicable Regulations</h3>
              <div className="flex flex-wrap gap-2">
                {result.applicable_regulations.map((r, i) => (
                  <span key={i} className="text-xs bg-blue-900/40 text-blue-300 px-2 py-1 rounded-full">{r}</span>
                ))}
              </div>
            </div>
          )}
          {result.compliance_gaps && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-red-400">Compliance Gaps</h3>
              {result.compliance_gaps.map((g, i) => (
                <div key={i} className="mb-3 text-sm border-b border-gray-800 pb-2">
                  <div className="flex justify-between items-start">
                    <span className="font-medium">{g.requirement}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${severityColor(g.severity)}`}>{g.severity}</span>
                  </div>
                  <p className="text-gray-400 text-xs mt-1">Gap: {g.gap}</p>
                  <p className="text-gray-500 text-xs">Risk: {g.risk}</p>
                </div>
              ))}
            </div>
          )}
          {result.corrective_actions && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="font-bold mb-2 text-green-400">Corrective Actions</h3>
              {result.corrective_actions.map((a, i) => (
                <div key={i} className="text-sm mb-1">
                  <span className="font-medium">[{a.priority}]</span> {a.action}
                  <span className="text-gray-400 text-xs ml-2">Due: {a.deadline_days} days</span>
                </div>
              ))}
            </div>
          )}
          {result.overall_compliance_score !== undefined && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <span className="text-2xl font-bold text-green-400">{(result.overall_compliance_score * 100).toFixed(0)}%</span>
              <p className="text-xs text-gray-500">Compliance Score</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
