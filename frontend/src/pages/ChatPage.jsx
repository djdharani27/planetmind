import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "../lib/api";
import * as vis from "vis-network/standalone";
import "vis-network/styles/vis-network.css";

/* ──────── Colour Palette ──────── */
const BG = "#FFFFFF",
  TEXT = "#0F172A",
  ACCENT = "#2563EB",
  ACCENT_HOVER = "#1D4ED8",
  GRAY_50 = "#F8FAFC",
  GRAY_100 = "#F1F5F9",
  GRAY_200 = "#E2E8F0",
  GRAY_300 = "#CBD5E1",
  GRAY_400 = "#94A3B8",
  GRAY_500 = "#64748B",
  GRAY_700 = "#334155";

/* ──────── Simple markdown renderer ──────── */
function Markdown({ text }) {
  const html = text
    .replace(/^### (.+)$/gm, "<h3 class='text-lg font-bold mt-2 mb-1'>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2 class='text-xl font-bold mt-3 mb-1'>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1 class='text-2xl font-bold mt-3 mb-2'>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^- (.+)$/gm, "<li class='ml-4 list-disc text-sm'>$1</li>")
    .replace(/> (.+)$/gm, "<blockquote class='border-l-2 border-[#2563EB] pl-3 italic text-[#64748B] my-1'>$1</blockquote>")
    .replace(/`(.+?)`/g, "<code class='bg-[#F1F5F9] text-[#2563EB] px-1 rounded text-xs font-mono'>$1</code>")
    .replace(/\n\n/g, "<br class='my-1'/>");

  return <div className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />;
}

/* ──────── Inline Knowledge Graph ──────── */
const GROUP_COLORS = {
  equipment: { border: "#60a5fa", background: "#dbeafe", highlight: "#60a5fa" },
  component: { border: "#2dd4bf", background: "#ccfbf1", highlight: "#2dd4bf" },
  failure: { border: "#f87171", background: "#fee2e2", highlight: "#f87171" },
  maintenanceactivity: { border: "#fbbf24", background: "#fef3c7", highlight: "#fbbf24" },
  technician: { border: "#34d399", background: "#d1fae5", highlight: "#34d399" },
  regulation: { border: "#c084fc", background: "#f3e8ff", highlight: "#c084fc" },
  document: { border: "#94a3b8", background: "#f1f5f9", highlight: "#94a3b8" },
  location: { border: "#fde047", background: "#fef9c3", highlight: "#fde047" },
  processparameter: { border: "#f472b6", background: "#fce7f3", highlight: "#f472b6" },
  Unknown: { border: "#94a3b8", background: "#f1f5f9", highlight: "#94a3b8" },
};

function InlineGraph({ nodes: rawNodes, edges: rawEdges }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !rawNodes?.length) return;
    if (networkRef.current) networkRef.current.destroy();

    const graphNodes = new vis.DataSet(
      rawNodes.map((n) => ({
        id: n.id,
        label: n.label?.length > 15 ? n.label.slice(0, 13) + "…" : n.label,
        group: n.group || "Unknown",
        title: `<b>${n.type || n.group}</b><br/>${n.label}`,
        value: 2,
      }))
    );

    const graphEdges = new vis.DataSet(
      rawEdges.map((e, i) => ({
        id: e.id || `e${i}`,
        from: e.from,
        to: e.to,
        label: e.label,
        arrows: "to",
        font: { size: 8, color: GRAY_400, strokeWidth: 0 },
        color: { color: GRAY_300, highlight: GRAY_500 },
        smooth: { type: "curvedCW", roundness: 0.15 },
      }))
    );

    const options = {
      nodes: {
        shape: "dot",
        size: 18,
        font: { size: 10, color: TEXT, face: "Inter, sans-serif" },
        borderWidth: 1.5,
        shadow: { enabled: true, size: 4 },
      },
      edges: { width: 1, selectionWidth: 2 },
      groups: GROUP_COLORS,
      physics: { enabled: false },
      interaction: {
        hover: true,
        tooltipDelay: 80,
        navigationButtons: true,
        zoomView: true,
        dragView: true,
      },
    };

    networkRef.current = new vis.Network(
      containerRef.current,
      { nodes: graphNodes, edges: graphEdges },
      options
    );

    return () => {
      if (networkRef.current) networkRef.current.destroy();
    };
  }, [rawNodes, rawEdges]);

  if (!rawNodes?.length) return null;

  return (
    <div className="mt-3 rounded-xl border border-[#E2E8F0] overflow-hidden bg-white">
      <div className="px-3 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between">
        <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wide">
          Knowledge Graph · {rawNodes.length} entities, {rawEdges.length} relationships
        </span>
      </div>
      <div ref={containerRef} style={{ height: "320px", width: "100%" }} />
      <div className="px-3 py-2 bg-[#F8FAFC] border-t border-[#E2E8F0] flex flex-wrap gap-2">
        {Object.entries(GROUP_COLORS).map(([group, colors]) =>
          rawNodes.some((n) => (n.group || "Unknown") === group) ? (
            <span key={group} className="flex items-center gap-1 text-[10px] text-[#64748B]">
              <span
                className="w-2.5 h-2.5 rounded-full border inline-block"
                style={{ backgroundColor: colors.background, borderColor: colors.border }}
              />
              {group}
            </span>
          ) : null
        )}
      </div>
    </div>
  );
}

/* ──────── Source button (collapsible) ──────── */
function SourceButton({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-[11px] text-[#64748B] hover:text-[#2563EB] bg-[#F8FAFC] hover:bg-[#EFF6FF] border border-[#E2E8F0] rounded-lg px-2.5 py-1 transition-colors"
      >
        {open ? "Hide sources" : `${sources.length} source${sources.length > 1 ? "s" : ""}`}
      </button>
      {open && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {sources.slice(0, 8).map((s, i) => (
            <span
              key={i}
              className="text-[11px] bg-[#F8FAFC] text-[#475569] px-2 py-0.5 rounded-md border border-[#E2E8F0]"
            >
              {s.filename || s.document_id?.slice(0, 10) || "doc"}
              {s.page ? ` p.${s.page}` : ""}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ──────── Typing dots ──────── */
function TypingDots() {
  return (
    <div className="flex gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-[#94A3B8] animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

/* ──────── Kumar Chat Page ──────── */
export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("auto");
  const [processDocs, setProcessDocs] = useState(null);
  const [processRunning, setProcessRunning] = useState(false);
  const bottomRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  // Load document status when switching to process mode
  const loadProcessStatus = useCallback(async () => {
    try {
      const data = await apiFetch("/documents?page=1&limit=100");
      setProcessDocs(data.documents || []);
    } catch {
      setProcessDocs([]);
    }
  }, []);

  useEffect(() => {
    if (mode === "process") {
      loadProcessStatus();
      const interval = setInterval(loadProcessStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [mode, loadProcessStatus]);

  const processAll = async () => {
    setProcessRunning(true);
    try {
      const data = await apiFetch("/agent/process", {
        method: "POST",
        body: JSON.stringify({}),
      });
      addMessage({
        role: "assistant",
        content: `**Batch processing complete**\n\n- ✅ Processed: ${data.processed || 0}\n- ❌ Failed: ${data.failed || 0}`,
        intent: "process",
      });
      loadProcessStatus();
    } catch (err) {
      addMessage({
        role: "assistant",
        content: `**Error:** ${err.message}`,
        intent: "error",
      });
    }
    setProcessRunning(false);
  };

  const processSingle = async (docId) => {
    setProcessRunning(true);
    try {
      const data = await apiFetch("/agent/process", {
        method: "POST",
        body: JSON.stringify({ document_id: docId }),
      });
      addMessage({
        role: "assistant",
        content: `**Processed:** \`${data.filename}\` → ${data.status}`,
        intent: "process",
      });
      loadProcessStatus();
    } catch (err) {
      addMessage({
        role: "assistant",
        content: `**Error processing document:** ${err.message}`,
        intent: "error",
      });
    }
    setProcessRunning(false);
  };

  const addMessage = (msg) => setMessages((prev) => [...prev, msg]);

  const sendQuery = async (queryText, forcedMode) => {
    const q = queryText || input;
    if (!q.trim() || loading) return;
    if (!queryText) setInput("");

    const activeMode = forcedMode || mode;

    addMessage({ role: "user", content: q });
    setLoading(true);

    try {
      const data = await apiFetch("/agent/query", {
        method: "POST",
        body: JSON.stringify({ query: q, top_k: 15, mode: activeMode }),
      });

      const msg = {
        role: "assistant",
        content: data.answer,
        intent: data.intent,
        tools: data.tools_used,
        confidence: data.confidence,
        sources: data.sources,
        graphData: data.graph_data,
        structuredData: data.structured_data,
        related: data.related,
      };
      addMessage(msg);
    } catch (err) {
      addMessage({
        role: "assistant",
        content: `**Error:** ${err.message || "Something went wrong. Please try again."}`,
        intent: "error",
        confidence: 0,
      });
    }
    setLoading(false);
  };

  const toolButtons = [
    { id: "auto", label: "🤖 Auto", desc: "Let me decide" },
    { id: "search", label: "🔍 Search", desc: "Find documents" },
    { id: "maintenance", label: "🔧 Maintenance", desc: "RCA & predictions" },
    { id: "compliance", label: "📋 Compliance", desc: "Gaps & audits" },
    { id: "lessons", label: "⚠️ Lessons", desc: "Incidents & risks" },
    { id: "graph", label: "🕸️ Graph", desc: "Knowledge graph" },
    { id: "process", label: "⚙️ Process", desc: "Embeddings & graphs" },
  ];

  const suggestions = {
    auto: [
      "Why did the turbine fail?",
      "Show me compliance gaps",
      "What lessons were learned?",
      "Show the knowledge graph",
    ],
    process: [
      "Show me processing status",
      "Process all pending documents",
    ],
  };

  const activeSuggestions = suggestions[mode] || suggestions.auto;

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-white text-[#0F172A]">
      {/* ────── Header ────── */}
      <div className="border-b border-[#E2E8F0] bg-[#F8FAFC] px-6 py-4 shrink-0">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#2563EB] flex items-center justify-center text-white font-bold text-lg shadow-sm">
              K
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#0F172A]">Kumar</h1>
              <p className="text-sm text-[#64748B]">Veteran · Industrial Intelligence</p>
            </div>
          </div>

          {/* Tool selector */}
          <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
            {toolButtons.map((t) => (
              <button
                key={t.id}
                onClick={() => setMode(t.id)}
                className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                  mode === t.id
                    ? "bg-[#2563EB] text-white border-[#2563EB] shadow-sm"
                    : "bg-white text-[#475569] border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB]"
                }`}
                title={t.desc}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ────── Messages ────── */}
      <div className="flex-1 overflow-y-auto px-4 md:px-6">
        <div className="max-w-5xl mx-auto py-6 space-y-5">
          {messages.length === 0 && !loading && mode === "process" ? (
            <ProcessDashboard
              docs={processDocs}
              loading={processDocs === null}
              processing={processRunning}
              onProcessAll={processAll}
              onProcessSingle={processSingle}
              onRefresh={loadProcessStatus}
            />
          ) : messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center pt-16 pb-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#2563EB]/10 flex items-center justify-center text-3xl mb-4">
                K
              </div>
              <h2 className="text-xl font-bold text-[#0F172A] mb-1">
                What do you need to know?
              </h2>
              <p className="text-sm text-[#64748B] max-w-md mb-6">
                I'm Kumar — a veteran in industrial intelligence. I only speak from the
                documents: no guesswork, no filler, just what the data says. Ask me about
                equipment, failures, maintenance, compliance, or operations.
              </p>
              <div className="grid grid-cols-2 gap-2 max-w-md w-full">
                {activeSuggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendQuery(s)}
                    className="text-sm text-[#475569] bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-2.5 hover:border-[#2563EB] hover:text-[#2563EB] transition-colors text-left"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 flex items-center justify-center text-sm font-bold text-[#2563EB] shrink-0">
                K
              </div>
              <div className="bg-white border border-[#E2E8F0] rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <TypingDots />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* ────── Input ────── */}
      <div className="border-t border-[#E2E8F0] bg-[#F8FAFC] px-4 md:px-6 py-3 shrink-0">
        <div className="max-w-5xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendQuery()}
            placeholder="Ask Kumar — what do the documents say?"
            className="flex-1 bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-sm text-[#0F172A] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30 focus:border-[#2563EB] transition-all"
            disabled={loading}
          />
          <button
            onClick={() => sendQuery()}
            disabled={loading || !input.trim()}
            className="bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 disabled:cursor-not-allowed px-5 py-3 rounded-xl text-sm font-medium text-white transition-colors shadow-sm"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

/* ──────── Process Dashboard ──────── */
function ProcessDashboard({ docs, loading, processing, onProcessAll, onProcessSingle, onRefresh }) {
  const byStatus = (status) => docs?.filter((d) => d.processing_status === status) || [];
  const pending = byStatus("uploaded");
  const failed = byStatus("failed");
  const completed = byStatus("completed");
  const inProgress = byStatus("processing");

  if (loading) {
    return (
      <div className="flex items-center justify-center pt-16">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-2 h-2 rounded-full bg-[#94A3B8] animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto pt-6 pb-4 space-y-4">
      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-[#0F172A]">{completed.length}</div>
          <div className="text-xs text-[#64748B] mt-1">Completed</div>
        </div>
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-[#2563EB]">{inProgress.length}</div>
          <div className="text-xs text-[#64748B] mt-1">Processing</div>
        </div>
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-[#f59e0b]">{pending.length}</div>
          <div className="text-xs text-[#64748B] mt-1">Pending</div>
        </div>
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-[#ef4444]">{failed.length}</div>
          <div className="text-xs text-[#64748B] mt-1">Failed</div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={onProcessAll}
          disabled={processing || (pending.length === 0 && failed.length === 0)}
          className="bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors"
        >
          {processing ? "Processing..." : `Process All Pending (${pending.length + failed.length})`}
        </button>
        <button
          onClick={onRefresh}
          disabled={processing}
          className="bg-white border border-[#E2E8F0] hover:border-[#2563EB] px-4 py-2 rounded-lg text-sm text-[#475569] hover:text-[#2563EB] transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Document list */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl overflow-hidden">
        <div className="px-4 py-3 bg-[#F8FAFC] border-b border-[#E2E8F0]">
          <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wide">Documents</span>
        </div>
        {!docs?.length ? (
          <div className="p-6 text-center text-sm text-[#94A3B8]">No documents uploaded yet. Go to Upload page first.</div>
        ) : (
          <div className="divide-y divide-[#E2E8F0]">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between px-4 py-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#0F172A] truncate">{doc.filename}</p>
                  <p className="text-xs text-[#64748B]">
                    {doc.file_type?.split("/").pop() || ""} · {(doc.file_size / 1024).toFixed(0)} KB
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={doc.processing_status} />
                  {(doc.processing_status === "uploaded" || doc.processing_status === "failed") && (
                    <button
                      onClick={() => onProcessSingle(doc.id)}
                      disabled={processing}
                      className="text-xs bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 text-white px-2.5 py-1 rounded-lg transition-colors"
                    >
                      Process
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    uploaded: "bg-[#fef3c7] text-[#92400e] border-[#fde68a]",
    processing: "bg-[#dbeafe] text-[#1e40af] border-[#bfdbfe]",
    completed: "bg-[#d1fae5] text-[#065f46] border-[#a7f3d0]",
    failed: "bg-[#fee2e2] text-[#991b1b] border-[#fecaca]",
  };
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full border font-medium ${colors[status] || "bg-[#f1f5f9] text-[#475569] border-[#e2e8f0]"}`}>
      {status}
    </span>
  );
}

/* ──────── Message Bubble ──────── */
function MessageBubble({ message }) {
  const { role, content, intent, sources, graphData } = message;

  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm"
          style={{ backgroundColor: ACCENT, color: "#FFFFFF" }}
        >
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-lg bg-[#2563EB]/10 flex items-center justify-center text-sm font-bold text-[#2563EB] shrink-0 mt-1">
        K
      </div>
      <div className="flex-1 min-w-0">
        <div className="bg-white border border-[#E2E8F0] rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          <span className="text-xs font-semibold text-[#2563EB] block mb-1.5">Kumar</span>

          <Markdown text={content} />

          <SourceButton sources={sources} />
        </div>

        {/* Inline knowledge graph */}
        {graphData?.nodes?.length > 0 && (
          <div className="mt-2 ml-2">
            <InlineGraph nodes={graphData.nodes} edges={graphData.edges} />
          </div>
        )}
      </div>
    </div>
  );
}
