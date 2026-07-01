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
  equipment: { border: "#3b82f6", background: "#dbeafe", highlight: "#3b82f6" },
  component: { border: "#06b6d4", background: "#cffafe", highlight: "#06b6d4" },
  failure: { border: "#ef4444", background: "#fee2e2", highlight: "#ef4444" },
  maintenanceactivity: { border: "#f59e0b", background: "#fef3c7", highlight: "#f59e0b" },
  technician: { border: "#10b981", background: "#d1fae5", highlight: "#10b981" },
  regulation: { border: "#a855f7", background: "#f3e8ff", highlight: "#a855f7" },
  document: { border: "#6b7280", background: "#f3f4f6", highlight: "#6b7280" },
  location: { border: "#ecc94b", background: "#fef9c3", highlight: "#ecc94b" },
  processparameter: { border: "#ec4899", background: "#fce7f3", highlight: "#ec4899" },
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
      physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -30,
          centralGravity: 0.005,
          springLength: 100,
          springConstant: 0.06,
        },
        stabilization: { iterations: 100 },
      },
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

/* ──────── Source badges ──────── */
function SourceBadges({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {sources.slice(0, 5).map((s, i) => (
        <span
          key={i}
          className="text-[11px] bg-[#F1F5F9] text-[#64748B] px-2 py-0.5 rounded-full border border-[#E2E8F0]"
        >
          {s.filename || s.document_id?.slice(0, 10) || "source"}
          {s.page ? ` p.${s.page}` : ""}
          {s.score != null && ` (${(s.score * 100).toFixed(0)}%)`}
        </span>
      ))}
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
  const bottomRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

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
  ];

  const suggestions = [
    "Why did the turbine fail?",
    "Show me compliance gaps",
    "What lessons were learned?",
    "Show the knowledge graph",
  ];

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
              <p className="text-sm text-[#64748B]">Intelligence for Industries</p>
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
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center pt-16 pb-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#2563EB]/10 flex items-center justify-center text-3xl mb-4">
                K
              </div>
              <h2 className="text-xl font-bold text-[#0F172A] mb-1">
                What do you need to know?
              </h2>
              <p className="text-sm text-[#64748B] max-w-md mb-6">
                I'm Kumar, your industrial intelligence agent. Ask me anything about
                equipment, failures, compliance, documents, or operations — I'll pull
                insights from all available data sources.
              </p>
              <div className="grid grid-cols-2 gap-2 max-w-md w-full">
                {suggestions.map((s) => (
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
            placeholder="Ask Kumar anything..."
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
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold text-[#2563EB]">Kumar</span>
            {intent && intent !== "chat" && intent !== "error" && (
              <span className="text-[10px] bg-[#EFF6FF] text-[#2563EB] px-1.5 py-0.5 rounded-full border border-[#BFDBFE] capitalize">
                {intent}
              </span>
            )}
          </div>

          <Markdown text={content} />

          {sources?.length > 0 && <SourceBadges sources={sources} />}
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
