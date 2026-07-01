import { useEffect, useRef, useState, useCallback } from "react";
import * as vis from "vis-network/standalone";
import "vis-network/styles/vis-network.css";
import { apiFetch } from "../lib/api";

const GROUP_COLORS = {
  equipment:        { border: "#3b82f6", background: "#1e3a5f", highlight: { background: "#2563eb", border: "#60a5fa" } },
  component:        { border: "#06b6d4", background: "#164e63", highlight: { background: "#0891b2", border: "#22d3ee" } },
  failure:          { border: "#ef4444", background: "#5f1a1a", highlight: { background: "#dc2626", border: "#f87171" } },
  maintenanceactivity: { border: "#f59e0b", background: "#5c3d0a", highlight: { background: "#d97706", border: "#fbbf24" } },
  technician:       { border: "#10b981", background: "#064e3b", highlight: { background: "#059669", border: "#34d399" } },
  regulation:       { border: "#a855f7", background: "#3b1a6e", highlight: { background: "#9333ea", border: "#c084fc" } },
  document:         { border: "#6b7280", background: "#1f2937", highlight: { background: "#4b5563", border: "#9ca3af" } },
  location:         { border: "#eab308", background: "#5c4a0a", highlight: { background: "#ca8a04", border: "#fef08a" } },
  processparameter: { border: "#ec4899", background: "#5c1442", highlight: { background: "#db2777", border: "#f472b6" } },
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
  const [physicsOn, setPhysicsOn] = useState(true);

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
        const size = 14 + (deg / maxDeg) * 36;
        return {
          id: n.id,
          label: n.label?.length > 18 ? n.label.slice(0, 16) + "…" : n.label,
          group: n.group || "Unknown",
          title: `<div style="font-size:13px;line-height:1.5">
            <b>${n.type || n.group}</b><br/>
            ${n.label}<br/>
            <span style="color:#9ca3af;font-size:11px">${deg} connection${deg !== 1 ? "s" : ""}</span>
          </div>`,
          value: deg,
          size,
          borderWidth: 2,
          borderWidthSelected: 3,
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
        font: {
          size: 8,
          color: "#6b7280",
          strokeWidth: 0,
          align: "middle",
        },
        color: { color: "#374151", highlight: "#6366f1", hover: "#6366f1" },
        smooth: { type: "continuous", roundness: 0.15 },
        width: 1,
        selectionWidth: () => 2.5,
        hoverWidth: 2,
      }))
    );

    const options = {
      nodes: {
        shape: "dot",
        font: {
          size: 11,
          color: "#d1d5db",
          face: "Inter, system-ui, sans-serif",
          strokeWidth: 2,
          strokeColor: "#111827",
        },
        shadow: {
          enabled: true,
          color: "rgba(0,0,0,0.4)",
          size: 6,
          x: 0,
          y: 2,
        },
        scaling: {
          min: 14,
          max: 50,
          label: { enabled: true, min: 9, max: 14 },
        },
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
      physics: {
        enabled: physicsOn,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -28,
          centralGravity: 0.003,
          springLength: 180,
          springConstant: 0.04,
          damping: 0.4,
          avoidOverlap: 0.6,
        },
        stabilization: {
          iterations: 300,
          updateInterval: 25,
          onlyDynamicEdges: false,
          fit: true,
        },
        timestep: 0.35,
        adaptiveTimestep: true,
      },
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
      layout: {
        improvedLayout: true,
        randomSeed: 42,
      },
    };

    const network = new vis.Network(containerRef.current, { nodes: graphNodes, edges: graphEdges }, options);
    networkRef.current = network;

    network.on("selectNode", (params) => {
      const nodeId = params.nodes[0];
      const node = nodes.find((n) => n.id === nodeId);
      setSelected({ ...node, degree: degrees[nodeId] || 0 });
    });
    network.on("deselectNode", () => setSelected(null));
    network.on("hoverNode", () => { document.body.style.cursor = "pointer"; });
    network.on("blurNode", () => { document.body.style.cursor = "default"; });

    network.on("stabilizationProgress", (params) => {
      if (params.iterations % 50 === 0) {
        const pct = Math.round((params.iterations / params.total) * 100);
        containerRef.current?.setAttribute("data-progress", `${pct}%`);
      }
    });
    network.once("stabilizationIterationsDone", () => {
      containerRef.current?.removeAttribute("data-progress");
    });
  }, [nodes, edges, physicsOn]);

  const togglePhysics = () => setPhysicsOn((p) => !p);

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
            <button
              onClick={togglePhysics}
              title={physicsOn ? "Freeze layout" : "Enable physics"}
              className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                physicsOn ? "bg-blue-600 hover:bg-blue-500" : "bg-gray-800 hover:bg-gray-700"
              }`}
            >
              {physicsOn ? "⏸ Freeze" : "▶ Animate"}
            </button>
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
