import { useEffect, useRef, useState, useCallback } from "react";
import * as vis from "vis-network/standalone";
import "vis-network/styles/vis-network.css";
import { apiFetch } from "../lib/api";

const GROUP_COLORS = {
  equipment:        { border: "#60a5fa", background: "#1e40af", highlight: { background: "#2563eb", border: "#93c5fd" } },
  component:        { border: "#2dd4bf", background: "#115e59", highlight: { background: "#0d9488", border: "#5eead4" } },
  failure:          { border: "#f87171", background: "#991b1b", highlight: { background: "#dc2626", border: "#fca5a5" } },
  maintenanceactivity: { border: "#fbbf24", background: "#92400e", highlight: { background: "#d97706", border: "#fde68a" } },
  technician:       { border: "#34d399", background: "#065f46", highlight: { background: "#059669", border: "#6ee7b7" } },
  regulation:       { border: "#c084fc", background: "#581c87", highlight: { background: "#9333ea", border: "#d8b4fe" } },
  document:         { border: "#94a3b8", background: "#334155", highlight: { background: "#475569", border: "#cbd5e1" } },
  location:         { border: "#fde047", background: "#854d0e", highlight: { background: "#ca8a04", border: "#fef08a" } },
  processparameter: { border: "#f472b6", background: "#831843", highlight: { background: "#db2777", border: "#f9a8d4" } },
};

const SHAPES = {
  equipment: "diamond",
  component: "hexagon",
  failure: "triangle",
  maintenanceactivity: "square",
  technician: "dot",
  regulation: "star",
  document: "box",
  location: "ellipse",
  processparameter: "dot",
};

function computeDegrees(edges) {
  const deg = {};
  for (const e of edges) {
    deg[e.from] = (deg[e.from] || 0) + 1;
    deg[e.to] = (deg[e.to] || 0) + 1;
  }
  return deg;
}

export default function GraphPage() {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [docId, setDocId] = useState("");
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const loadGraph = useCallback(async (path) => {
    setLoading(true);
    try {
      const data = await apiFetch(path);
      if (data.warning) {
        setSelected({ type: "warning", message: data.warning });
        setNodes([]);
        setEdges([]);
      } else {
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
        setSelected(null);
      }
    } catch {
      setSelected({ type: "error", message: "Failed to load graph" });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadGraph("/graph");
    return () => { if (networkRef.current) networkRef.current.destroy(); };
  }, [loadGraph]);

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return;
    if (networkRef.current) networkRef.current.destroy();

    const degrees = computeDegrees(edges);
    const maxDeg = Math.max(...Object.values(degrees), 1);

    const graphNodes = new vis.DataSet(
      nodes.map((n) => {
        const deg = degrees[n.id] || 1;
        const size = 18 + (deg / maxDeg) * 32;
        const group = n.group || "Unknown";
        return {
          id: n.id,
          label: n.label?.length > 14 ? n.label.slice(0, 12) + "…" : n.label,
          group,
          shape: SHAPES[group] || "dot",
          title: `<div style="font-size:13px;line-height:1.6;padding:4px">
            <b style="color:${GROUP_COLORS[group]?.border || '#94a3b8'}">${n.type || group}</b><br/>
            <span style="font-size:14px">${n.label}</span><br/>
            <span style="color:#9ca3af;font-size:11px">${deg} connection${deg !== 1 ? "s" : ""}</span>
          </div>`,
          value: deg,
          size,
          borderWidth: deg > maxDeg * 0.5 ? 3 : 2,
          borderWidthSelected: 4,
        };
      })
    );

    const graphEdges = new vis.DataSet(
      edges.map((e, i) => ({
        id: e.id || `e${i}`,
        from: e.from,
        to: e.to,
        label: e.label,
        title: e.label,
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        font: { size: 8, color: "#6b7280", strokeWidth: 0, align: "middle" },
        color: { color: "#374151", highlight: "#6366f1", hover: "#6366f1" },
        smooth: { type: "continuous", roundness: 0.15 },
        width: 1,
        selectionWidth: () => 2.5,
        hoverWidth: 2,
      }))
    );

    const options = {
      nodes: {
        font: {
          size: 10,
          color: "#e2e8f0",
          face: "Inter, system-ui, sans-serif",
          strokeWidth: 3,
          strokeColor: "#0f172a",
        },
        shadow: {
          enabled: true,
          color: "rgba(0,0,0,0.5)",
          size: 8,
          x: 0,
          y: 3,
        },
        borderWidth: 2,
        borderWidthSelected: 4,
        scaling: { min: 16, max: 50, label: { enabled: true, min: 8, max: 13 } },
      },
      edges: {
        width: 1,
        selectionWidth: 2.5,
        hoverWidth: 2,
        color: { color: "#374151", highlight: "#6366f1", hover: "#6366f1" },
        smooth: { type: "continuous", roundness: 0.15 },
        font: { size: 8, color: "#6b7280", strokeWidth: 0, align: "middle" },
      },
      groups: GROUP_COLORS,
      physics: { enabled: false },
      layout: { improvedLayout: true, randomSeed: 42 },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        navigationButtons: true,
        keyboard: { enabled: true },
        zoomView: true,
        dragView: true,
        hoverConnectedEdges: true,
        selectConnectedEdges: true,
      },
    };

    const network = new vis.Network(containerRef.current, { nodes: graphNodes, edges: graphEdges }, options);
    networkRef.current = network;

    network.on("selectNode", (params) => {
      const nodeId = params.nodes[0];
      const node = nodes.find((n) => n.id === nodeId);
      if (node) setSelected({ ...node, degree: degrees[nodeId] || 0 });
    });
    network.on("deselectNode", () => setSelected(null));
    network.on("hoverNode", () => { document.body.style.cursor = "pointer"; });
    network.on("blurNode", () => { document.body.style.cursor = "default"; });
  }, [nodes, edges]);

  const zoomIn = () => networkRef.current?.zoomIn(0.4);
  const zoomOut = () => networkRef.current?.zoomOut(0.4);
  const resetView = () => networkRef.current?.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });

  const loadForDoc = () => {
    if (!docId.trim()) return;
    loadGraph(`/graph/${docId.trim()}`);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-6">
      {/* Header */}
      <div className="max-w-full mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-3">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">Knowledge Graph</h1>
            <p className="text-gray-400 text-sm mt-1">
              {nodes.length > 0
                ? `${nodes.length} entities · ${edges.length} relationships`
                : "Interactive graph of entities, equipment, failures, and relationships"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => loadGraph("/graph")}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              {loading ? "Loading…" : "Full Graph"}
            </button>
          </div>
        </div>

        {/* Controls bar */}
        <div className="flex flex-col md:flex-row gap-2 mb-4">
          <div className="flex-1 flex gap-2">
            <input
              value={docId}
              onChange={(e) => setDocId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadForDoc()}
              placeholder="Filter by document ID…"
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
            />
            <button
              onClick={loadForDoc}
              disabled={loading || !docId.trim()}
              className="bg-gray-700 hover:bg-gray-600 disabled:opacity-40 px-4 py-2 rounded-lg text-sm transition-colors"
            >
              Filter
            </button>
          </div>
          <div className="flex gap-1.5">
            <button onClick={zoomIn} title="Zoom in" className="bg-gray-800 hover:bg-gray-700 px-2.5 py-2 rounded-lg text-sm transition-colors">＋</button>
            <button onClick={zoomOut} title="Zoom out" className="bg-gray-800 hover:bg-gray-700 px-2.5 py-2 rounded-lg text-sm transition-colors">−</button>
            <button onClick={resetView} title="Fit view" className="bg-gray-800 hover:bg-gray-700 px-2.5 py-2 rounded-lg text-sm transition-colors">⊞</button>
          </div>
        </div>

        {/* Messages */}
        {selected?.type === "warning" && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-4 mb-4 text-yellow-300 text-sm">
            {selected.message}
          </div>
        )}
        {selected?.type === "error" && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-4 text-red-300 text-sm">
            {selected.message}
          </div>
        )}

        {/* Graph + sidebar */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <div
              ref={containerRef}
              className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
              style={{ minHeight: "520px", height: "65vh" }}
            />
            {nodes.length === 0 && !loading && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <p className="text-gray-600 text-sm">No graph data available</p>
              </div>
            )}
            {/* Loading overlay */}
            {loading && (
              <div className="absolute top-3 right-3 bg-gray-900/80 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-400 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                Loading…
              </div>
            )}
          </div>

          {selected && selected.id && (
            <div className="lg:w-72 bg-gray-900 rounded-xl border border-gray-800 p-4 shrink-0 max-h-[65vh] overflow-y-auto">
              <div
                className="w-full h-1 rounded-full mb-3"
                style={{ backgroundColor: (GROUP_COLORS[selected.group] || GROUP_COLORS.document).background }}
              />
              <h3 className="font-bold text-lg mb-1 break-words">{selected.label}</h3>
              {selected.degree !== undefined && (
                <p className="text-xs text-gray-500 mb-3">{selected.degree} connection{selected.degree !== 1 ? "s" : ""}</p>
              )}
              <div className="space-y-2 text-sm border-t border-gray-800 pt-3">
                {[
                  { label: "Type", value: selected.type },
                  { label: "Group", value: selected.group },
                  { label: "ID", value: selected.id, mono: true },
                ].map((f) => (
                  <div key={f.label}>
                    <span className="text-gray-500 text-[10px] uppercase tracking-wider">{f.label}</span>
                    <p className={`${f.mono ? "text-xs font-mono text-gray-400 break-all" : "text-sm"}`}>{f.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Legend */}
        {nodes.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5">
            {Object.entries(GROUP_COLORS).map(([group, colors]) =>
              nodes.some((n) => n.group === group) ? (
                <div key={group} className="flex items-center gap-1.5 text-xs text-gray-400">
                  <span
                    className="w-2.5 h-2.5 rounded-full border shrink-0"
                    style={{ backgroundColor: (colors.highlight || colors).background || colors.background, borderColor: colors.border }}
                  />
                  {group}
                </div>
              ) : null
            )}
          </div>
        )}
      </div>
    </div>
  );
}
