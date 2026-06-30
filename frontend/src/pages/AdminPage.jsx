import { useState } from "react";
import { apiFetch } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function AdminPage() {
  const { user } = useAuth();
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  if (user?.role !== "admin") {
    return (
      <div className="p-8 text-center">
        <p className="text-red-400 text-lg">Access denied — admin role required</p>
      </div>
    );
  }

  const nuke = async () => {
    setLoading(true);
    setResult(null);
    try {
      const data = await apiFetch("/admin/nuke", { method: "POST" });
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setLoading(false);
    setConfirm(false);
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-2 text-red-400">Admin Panel</h1>
      <p className="text-gray-400 mb-8 text-sm">Danger zone — irreversible operations</p>

      <div className="bg-red-950/30 border border-red-800 rounded-xl p-6">
        <h2 className="text-lg font-bold text-red-400 mb-2">Nuclear Delete</h2>
        <p className="text-gray-400 text-sm mb-4">
          Deletes everything: all documents, SQLite records, uploaded files, processed outputs, Qdrant vector embeddings, and Neo4j knowledge graph. This cannot be undone.
        </p>

        {!confirm ? (
          <button
            onClick={() => setConfirm(true)}
            className="bg-red-700 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            Delete Everything
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-red-300 text-sm font-medium">Are you absolutely sure?</p>
            <div className="flex gap-3">
              <button
                onClick={nuke}
                disabled={loading}
                className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
              >
                {loading ? "Nuking..." : "Yes, Delete Everything"}
              </button>
              <button
                onClick={() => setConfirm(false)}
                className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-4 bg-gray-900 rounded-lg p-4 text-sm">
            {result.error ? (
              <p className="text-red-400">{result.error}</p>
            ) : (
              <div className="space-y-1">
                <p className="text-green-400 font-medium">✓ Nuked successfully</p>
                <p className="text-gray-400">Documents deleted: {result.details?.sqlite_documents}</p>
                <p className="text-gray-400">Storage wiped: {result.details?.storage_deleted ? "Yes" : "No"}</p>
                <p className="text-gray-400">Qdrant cleared: {result.details?.qdrant_cleared ? "Yes" : "No"}</p>
                <p className="text-gray-400">Neo4j cleared: {result.details?.neo4j_cleared ? "Yes" : "No"}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
