import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

export default function DocViewer() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("metadata");
  const [ocrData, setOcrData] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [entitiesData, setEntitiesData] = useState(null);
  const [chunksData, setChunksData] = useState(null);
  const [processStatus, setProcessStatus] = useState(null);
  const [runningJob, setRunningJob] = useState(null);

  useEffect(() => {
    fetch(`/api/documents/${id}`)
      .then((r) => r.json())
      .then((d) => {
        setDoc(d);
        setLoading(false);
        if (d.processing_status === "ready") loadProcessedData();
      })
      .catch(() => setLoading(false));
  }, [id]);

  const loadProcessedData = async () => {
    try {
      const [ocrRes, parsedRes, entitiesRes, chunksRes] = await Promise.all([
        fetch(`/storage/processed/${id}/ocr_output.json`).catch(() => null),
        fetch(`/storage/processed/${id}/parsed_output.json`).catch(() => null),
        fetch(`/storage/processed/${id}/entities.json`).catch(() => null),
        fetch(`/storage/processed/${id}/chunks.json`).catch(() => null),
      ]);
      if (ocrRes?.ok) setOcrData(await ocrRes.json());
      if (parsedRes?.ok) setParsedData(await parsedRes.json());
      if (entitiesRes?.ok) setEntitiesData(await entitiesRes.json());
      if (chunksRes?.ok) setChunksData(await chunksRes.json());
    } catch {}
  };

  const process = async () => {
    setProcessStatus("starting");
    try {
      const res = await fetch("/api/pipeline/process-async", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: id }),
      });
      const data = await res.json();
      setRunningJob(data.job_id);
      pollJob(data.job_id);
    } catch {
      setProcessStatus("failed");
    }
  };

  const pollJob = (jobId) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/pipeline/job/${jobId}`);
        const job = await res.json();
        setProcessStatus(job);
        if (job.status === "completed" || job.status === "failed") {
          clearInterval(interval);
          const refreshed = await fetch(`/api/documents/${id}`).then((r) => r.json());
          setDoc(refreshed);
          if (job.status === "completed") loadProcessedData();
          setRunningJob(null);
        }
      } catch {
        clearInterval(interval);
      }
    }, 1000);
  };

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;
  if (!doc) return <div className="p-8 text-red-400">Document not found</div>;

  const tabs = ["metadata", "text", "parsed", "entities", "chunks"];

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start gap-3 mb-6">
        <div>
          <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-300 text-sm mb-1">← Back</button>
          <h1 className="text-xl md:text-2xl font-bold">{doc.filename}</h1>
          <p className="text-gray-400 text-xs mt-1">{doc.file_type?.split("/")[1]?.toUpperCase()} · {(doc.file_size / 1024).toFixed(1)} KB · {doc.upload_timestamp ? new Date(doc.upload_timestamp).toLocaleString() : ""}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full ${
            doc.processing_status === "ready" ? "bg-green-600" : doc.processing_status === "failed" ? "bg-red-600" : doc.processing_status === "processing" ? "bg-yellow-600" : "bg-blue-600"
          }`}>
            {doc.processing_status}
          </span>
          {(doc.processing_status === "uploaded" || doc.processing_status === "failed") && (
            <button onClick={process} disabled={processStatus === "processing"} className="bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 px-3 py-1 rounded text-sm font-medium whitespace-nowrap">
              Process
            </button>
          )}
        </div>
      </div>

      {processStatus && processStatus.steps && (
        <div className="bg-gray-900 rounded-xl p-4 mb-4 border border-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-medium">Pipeline Progress</span>
            <div className="flex-1 bg-gray-800 rounded-full h-2">
              <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${processStatus.progress || 0}%` }} />
            </div>
            <span className="text-xs text-gray-400">{processStatus.progress || 0}%</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(processStatus.steps).map(([step, status]) => (
              <div key={step} className="flex items-center gap-1.5 text-xs">
                <span className={`w-2 h-2 rounded-full ${status === "complete" ? "bg-green-400" : status === "running" ? "bg-yellow-400 animate-pulse" : status === "failed" ? "bg-red-400" : "bg-gray-600"}`} />
                <span className="text-gray-400 capitalize">{step}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1 mb-4 flex-wrap">
        {tabs.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 md:px-4 py-2 text-sm rounded-lg capitalize ${tab === t ? "bg-gray-800 text-white" : "text-gray-400 hover:text-gray-200"}`}>
            {t}
          </button>
        ))}
      </div>

      <div className="bg-gray-900 rounded-xl p-4 md:p-6 border border-gray-800 max-h-[70vh] overflow-y-auto">
        {tab === "metadata" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(doc).filter(([k]) => k !== "storage_path").map(([k, v]) => (
              <div key={k}>
                <p className="text-xs text-gray-500 uppercase">{k}</p>
                <p className="text-sm truncate">{typeof v === "object" ? JSON.stringify(v) : String(v)}</p>
              </div>
            ))}
          </div>
        )}
        {tab === "text" && (
          <div className="text-sm text-gray-300">
            {ocrData ? (
              <div>
                <p className="text-xs text-gray-500 mb-2">
                  Pages: {ocrData.pages?.length || 0} · Avg Confidence: {((ocrData.avg_confidence || 0) * 100).toFixed(1)}%
                </p>
                <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">{ocrData.total_text}</pre>
              </div>
            ) : (
              <p className="text-gray-500">No OCR text yet. Process the document first.</p>
            )}
          </div>
        )}
        {tab === "parsed" && (
          <div className="text-sm text-gray-300">
            {parsedData ? (
              <div>
                <p className="text-xs text-gray-500 mb-2">Sections: {parsedData.sections?.length || 0} · Title: {parsedData.title || "N/A"}</p>
                {parsedData.sections?.map((s, i) => (
                  <div key={i} className="mb-4 border-b border-gray-800 pb-3">
                    <h3 className="font-bold text-base mb-1">{s.heading || `Section ${i + 1}`}</h3>
                    {s.paragraphs?.map((p, pi) => <p key={pi} className="text-gray-400 mb-1">{p}</p>)}
                    {s.tables?.map((t, ti) => (
                      <div key={ti} className="my-2 overflow-x-auto">
                        <table className="text-xs border border-gray-700">
                          <tbody>
                            {t.map((row, ri) => (
                              <tr key={ri}>{row.map((cell, ci) => <td key={ci} className="border border-gray-700 px-2 py-1">{cell}</td>)}</tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No parsed structure yet.</p>
            )}
          </div>
        )}
        {tab === "entities" && (
          <div className="text-sm text-gray-300">
            {entitiesData ? (
              <div>
                <p className="text-xs text-gray-500 mb-2">Entities: {entitiesData.length || 0}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {entitiesData.map((e, i) => (
                    <div key={i} className="bg-gray-800 rounded-lg p-2 text-xs">
                      <span className="bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded text-xs mr-1">{e.type}</span>
                      <span className="font-medium">{e.value}</span>
                      {e.confidence && <span className="text-gray-500 ml-1">({(e.confidence * 100).toFixed(0)}%)</span>}
                      {e.context && <p className="text-gray-500 mt-1 truncate">{e.context}</p>}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No entities extracted yet.</p>
            )}
          </div>
        )}
        {tab === "chunks" && (
          <div className="text-sm text-gray-300">
            {chunksData ? (
              <div>
                <p className="text-xs text-gray-500 mb-2">Chunks: {chunksData.length || 0}</p>
                {chunksData.map((c, i) => (
                  <div key={i} className="mb-3 p-3 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="flex justify-between items-center text-xs text-gray-500 mb-1">
                      <span className="font-mono">{c.chunk_id}</span>
                      <span>Page {c.page_number} · {c.section || "—"}</span>
                    </div>
                    <p className="text-gray-300 leading-relaxed">{c.chunk_text}</p>
                    <div className="flex gap-3 mt-1 text-xs text-gray-600">
                      {c.previous_chunk_id && <span>← {c.previous_chunk_id.split("_c").pop()}</span>}
                      {c.next_chunk_id && <span>{c.next_chunk_id.split("_c").pop()} →</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No chunks yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
