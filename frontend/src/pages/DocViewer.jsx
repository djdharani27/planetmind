import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

export default function DocViewer() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("metadata");
  const [processStatus, setProcessStatus] = useState(null);

  useEffect(() => {
    fetch(`/api/documents/${id}`)
      .then((r) => r.json())
      .then((d) => { setDoc(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  const process = async () => {
    setProcessStatus("processing");
    try {
      const res = await fetch("/api/pipeline/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: id }),
      });
      const data = await res.json();
      setProcessStatus(data);
      const refreshed = await fetch(`/api/documents/${id}`).then((r) => r.json());
      setDoc(refreshed);
    } catch {
      setProcessStatus("failed");
    }
  };

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;
  if (!doc) return <div className="p-8 text-red-400">Document not found</div>;

  const tabs = ["metadata", "text", "entities", "chunks"];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold">{doc.filename}</h1>
          <p className="text-gray-400 text-sm mt-1">{doc.file_type} · {(doc.file_size / 1024).toFixed(1)} KB · {doc.upload_timestamp}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-1 rounded-full ${
            doc.processing_status === "ready" ? "bg-green-600" : doc.processing_status === "failed" ? "bg-red-600" : "bg-blue-600"
          }`}>
            {doc.processing_status}
          </span>
          {doc.processing_status === "uploaded" && (
            <button onClick={process} className="bg-yellow-600 hover:bg-yellow-700 px-3 py-1 rounded text-sm font-medium">
              {processStatus === "processing" ? "Processing..." : "Process"}
            </button>
          )}
        </div>
      </div>

      {processStatus && processStatus !== "processing" && processStatus.status === "ready" && (
        <div className="bg-green-900/50 border border-green-700 rounded-xl p-4 mb-4">
          <p className="text-green-300 font-medium">Processing Complete</p>
          <div className="flex gap-3 text-xs text-green-400 mt-1">
            {Object.entries(processStatus.steps).map(([step, result]) => (
              <span key={step}>{step}: {result}</span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1 mb-4">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm rounded-lg capitalize ${tab === t ? "bg-gray-800 text-white" : "text-gray-400 hover:text-gray-200"}`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        {tab === "metadata" && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(doc).map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-gray-500 uppercase">{k}</p>
                  <p className="text-sm truncate">{typeof v === "object" ? JSON.stringify(v) : String(v)}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {tab === "text" && (
          <div className="text-sm text-gray-300">
            <p className="text-gray-500 mb-2">OCR text and parsed content will appear here after processing.</p>
            <pre className="whitespace-pre-wrap font-mono text-xs">
              {doc.metadata?.ocr_text || "No text extracted yet."}
            </pre>
          </div>
        )}
        {tab === "entities" && (
          <div className="text-sm text-gray-300">
            <p className="text-gray-500 mb-2">Extracted entities will appear here after processing.</p>
            <pre className="whitespace-pre-wrap font-mono text-xs">
              {JSON.stringify(doc.metadata?.entities || {}, null, 2) || "No entities extracted yet."}
            </pre>
          </div>
        )}
        {tab === "chunks" && (
          <div className="text-sm text-gray-300">
            <p className="text-gray-500 mb-2">Document chunks will appear here after processing.</p>
            <p>Chunk count: {doc.metadata?.chunk_count || "N/A"}</p>
          </div>
        )}
      </div>
    </div>
  );
}
