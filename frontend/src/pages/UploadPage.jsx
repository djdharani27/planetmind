import { useState, useRef, useCallback, useEffect } from "react";
import { apiFetch, apiUpload } from "../lib/api";

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [status, setStatus] = useState(null);
  const inputRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    try {
      const data = await apiFetch("/documents");
      setDocuments(data.documents || []);
    } catch {
      setDocuments([]);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...dropped]);
  }, []);

  const handleSelect = useCallback((e) => {
    const selected = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...selected]);
  }, []);

  const removeFile = (idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const uploadAll = async () => {
    if (!files.length) return;
    setUploading(true);
    setStatus(null);

    let ok = 0;
    let fail = 0;

    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        await apiUpload("/documents/upload", form);
        ok++;
      } catch {
        fail++;
      }
    }

    setStatus(`${ok} uploaded, ${fail} failed — processing started`);
    setFiles([]);
    setUploading(false);
    fetchDocs();
    setTimeout(fetchDocs, 3000);
    setTimeout(fetchDocs, 8000);
  };

  const formatSize = (bytes) => {
    if (!bytes) return "0 B";
    const u = ["B", "KB", "MB", "GB"];
    let i = 0;
    let s = bytes;
    while (s >= 1024 && i < u.length - 1) {
      s /= 1024;
      i++;
    }
    return `${s.toFixed(1)} ${u[i]}`;
  };

  const statusColors = {
    uploaded: "bg-blue-600",
    processing: "bg-yellow-500",
    completed: "bg-green-500",
    failed: "bg-red-500",
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Document Upload</h1>
        <p className="text-gray-400 mb-8">
          Upload PDF, DOCX, JPG, PNG — maintenance reports, SOPs, manuals, incident records
        </p>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors mb-6 ${
            dragOver ? "border-blue-400 bg-blue-500/10" : "border-gray-600 hover:border-gray-400 bg-gray-900"
          }`}
        >
          <div className="text-4xl mb-3">📄</div>
          <p className="text-lg mb-1">Drag & drop files here</p>
          <p className="text-sm text-gray-500">or click to browse — PDF, DOCX, JPG, PNG (max 100 MB)</p>
          <input ref={inputRef} type="file" multiple accept=".pdf,.docx,.jpg,.jpeg,.png" className="hidden" onChange={handleSelect} />
        </div>

        {/* File queue */}
        {files.length > 0 && (
          <div className="bg-gray-900 rounded-xl p-4 mb-6">
            <div className="flex justify-between items-center mb-3">
              <span className="font-medium">{files.length} file(s) queued</span>
              <button
                onClick={uploadAll}
                disabled={uploading}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium"
              >
                {uploading ? "Uploading..." : "Upload All"}
              </button>
            </div>
            {files.map((f, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b border-gray-800 last:border-0">
                <div className="flex-1 min-w-0">
                  <p className="truncate">{f.name}</p>
                  <p className="text-xs text-gray-500">{formatSize(f.size)}</p>
                </div>
                <button onClick={() => removeFile(i)} className="text-red-400 hover:text-red-300 ml-3 text-sm">Remove</button>
              </div>
            ))}
          </div>
        )}

        {/* Status */}
        {status && (
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-6 text-center text-green-400">{status}</div>
        )}

        {/* Document list */}
        <h2 className="text-xl font-bold mb-4">Uploaded Documents</h2>
        {documents.length === 0 ? (
          <p className="text-gray-500">No documents yet.</p>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.id} className="bg-gray-900 rounded-xl p-4 flex justify-between items-center">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{doc.filename}</p>
                  <div className="flex gap-3 text-xs text-gray-400 mt-1">
                    <span>{doc.file_type?.split("/")[1]?.toUpperCase() || doc.file_type}</span>
                    <span>{formatSize(doc.file_size)}</span>
                    <span>{new Date(doc.upload_timestamp).toLocaleDateString()}</span>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${statusColors[doc.processing_status] || "bg-gray-600"}`}>
                  {doc.processing_status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
