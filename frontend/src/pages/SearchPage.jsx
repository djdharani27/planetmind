import { useState } from "react";
import { useNavigate } from "react-router-dom";

const FILTERS = [
  { key: "equipment", label: "Equipment" },
  { key: "date_from", label: "From Date" },
  { key: "date_to", label: "To Date" },
  { key: "type", label: "Document Type" },
  { key: "technician", label: "Technician" },
  { key: "failure", label: "Failure Type" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 15 }),
      });
      const data = await res.json();
      setResults(data);
    } catch {
      setResults(null);
    }
    setLoading(false);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Search</h1>
      <p className="text-gray-400 mb-6">Search across all documents — equipment, failures, procedures</p>

      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder='e.g., "gearbox inspection" or "Pump P-204"'
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          onClick={search}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-lg text-sm font-medium"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        {FILTERS.map((f) => (
          <div key={f.key} className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs">
            <span className="text-gray-400">{f.label}</span>
            {f.key.startsWith("date") ? (
              <input type="date" className="bg-transparent text-white text-xs focus:outline-none" />
            ) : (
              <input
                type="text"
                placeholder="any"
                className="bg-transparent text-white text-xs w-20 focus:outline-none"
              />
            )}
          </div>
        ))}
      </div>

      {results && (
        <>
          <div className="flex gap-4 mb-4 text-sm text-gray-400">
            <span>{results.results.length} results</span>
            {results.source_breakdown && (
              <>
                <span>BM25: {results.source_breakdown.bm25}</span>
                <span>Vector: {results.source_breakdown.vector}</span>
                <span>Graph: {results.source_breakdown.graph}</span>
              </>
            )}
          </div>
          <div className="space-y-3">
            {results.results.map((r, i) => (
              <div
                key={i}
                onClick={() => r.document_id && navigate(`/documents/${r.document_id}`)}
                className="bg-gray-900 rounded-xl p-4 border border-gray-800 cursor-pointer hover:border-gray-600 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs bg-gray-800 px-2 py-0.5 rounded-full">{r.source}</span>
                  <span className="text-xs text-gray-500">Score: {(r.rerank_score || r.score).toFixed(3)}</span>
                </div>
                <p className="text-sm text-gray-200 mb-1 font-medium">
                  {r.filename || r.document_id || r.entity}
                </p>
                <p className="text-xs text-gray-500 line-clamp-2">{r.snippet}</p>
                {r.page_number && <p className="text-xs text-gray-600 mt-1">Page {r.page_number}</p>}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
