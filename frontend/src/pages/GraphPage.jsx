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
  for (const e of edges) deg[e.from] = (deg[e.from] || 0) + 1, deg[e.to] = (deg[e.to] || 0) + 1;
  return deg;
}

export default function GraphPage() {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [legend, setLegend] = useState(false);

  const loadGraph = useCallback(async (path) => {
    setLoading(true);
    try {
      const data = await apiFetch(path);
      if (data.warning) {
        setSelected({ type: "warning", message: data.warning });
        setNodes([]); setEdges([]);
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
    return () => networkRef.current?.destroy();
  }, [loadGraph]);

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return;
    networkRef.current?.destroy();

    const degrees = computeDegrees(edges);
    const maxDeg = Math.max(...Object.values(degrees), 1);

    const vNodes = new vis.DataSet(nodes.map((n) => {
      const deg = degrees[n.id] || 1;
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
        size: 16 + (deg / maxDeg) * 34,
        borderWidth: deg > maxDeg * 0.5 ? 3 : 2,
        borderWidthSelected: 4,
      };
    }));

    const vEdges = new vis.DataSet(edges.map((e, i) => ({
      id: e.id || `e${i}`,
      from: e.from, to: e.to,
      arrows: { to: { enabled: true, scaleFactor: 0.5 } },
      color: { color: "#374151", highlight: "#6366f1", hover: "#6366f1" },
      smooth: { type: "continuous", roundness: 0.15 },
      width: 1,
    })));

    const net = new vis.Network(containerRef.current, { nodes: vNodes, edges: vEdges }, {
      nodes: {
        font: { size: 10, color: "#e2e8f0", face: "Inter, system-ui, sans-serif", strokeWidth: 3, strokeColor: "#0f172a" },
        shadow: { enabled: true, color: "rgba(0,0,0,0.5)", size: 8, x: 0, y: 3 },
        borderWidth: 2, borderWidthSelected: 4,
        scaling: { min: 16, max: 50, label: { enabled: true, min: 8, max: 13 } },
      },
      edges: {
        width: 1, color: { color: "#374151", highlight: "#6366f1", hover: "#6366f1" },
        smooth: { type: "continuous", roundness: 0.15 },
      },
      groups: GROUP_COLORS,
      physics: {
        solver: "barnesHut",
        barnesHut: { gravitationalConstant: -2000, centralGravity: 0.1, springLength: 120, springConstant: 0.04, damping: 0.5 },
        stabilization: { iterations: 80, updateInterval: 25, fit: true },
        timestep: 0.3,
      },
      layout: { improvedLayout: false },
      interaction: {
        hover: true, tooltipDelay: 150, navigationButtons: true,
        keyboard: { enabled: true }, zoomView: true, dragView: true,
        hoverConnectedEdges: true, selectConnectedEdges: true,
      },
    });

    net.once("stabilizationIterationsDone", () => {
      net.setOptions({ physics: { enabled: false } });
      net.fit({ animation: { duration: 300, easingFunction: "easeInOutQuad" } });
    });

    net.on("selectNode", (p) => {
      const node = nodes.find((n) => n.id === p.nodes[0]);
      if (node) setSelected({ ...node, degree: degrees[node.id] || 0 });
    });
    net.on("deselectNode", () => setSelected(null));
    net.on("hoverNode", () => { document.body.style.cursor = "pointer"; });
    net.on("blurNode", () => { document.body.style.cursor = "default"; });

    networkRef.current = net;
  }, [nodes, edges]);

  const zoomIn = () => networkRef.current?.zoomIn(0.4);
  const zoomOut = () => networkRef.current?.zoomOut(0.4);
  const resetView = () => networkRef.current?.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });

  return (
    <div className="relative w-screen h-screen bg-gray-950 overflow-hidden">
      {/* Graph canvas */}
      <div ref={containerRef} className="absolute inset-0" />

      {nodes.length === 0 && !loading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-gray-600 text-sm">No graph data available</p>
        </div>
      )}

      {/* Top bar — minimal */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-3 bg-gradient-to-b from-gray-950/90 to-transparent pointer-events-none">
        <div className="pointer-events-auto">
          <h1 className="text-lg font-bold text-white">Knowledge Graph</h1>
          <p className="text-xs text-gray-400">
            {nodes.length > 0 ? `${nodes.length} entities · ${edges.length} relationships` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2 pointer-events-auto">
          <button onClick={() => loadGraph("/graph")} disabled={loading}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors">
            {loading ? "…" : "Full Graph"}
          </button>
          <button onClick={() => setLegend((l) => !l)}
            className="bg-gray-800 hover:bg-gray-700 px-2.5 py-1.5 rounded-lg text-xs transition-colors">
            Legend
          </button>
        </div>
      </div>

      {/* Zoom controls — bottom right */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1 pointer-events-auto">
        <button onClick={zoomIn} className="bg-gray-800 hover:bg-gray-700 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors">＋</button>
        <button onClick={zoomOut} className="bg-gray-800 hover:bg-gray-700 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors">−</button>
        <button onClick={resetView} className="bg-gray-800 hover:bg-gray-700 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors" title="Fit">⊞</button>
      </div>

      {/* Legend panel */}
      {legend && (
        <div className="absolute bottom-4 left-4 bg-gray-900/95 border border-gray-700 rounded-xl px-3 py-2.5 text-xs shadow-xl backdrop-blur-sm">
          <p className="text-gray-400 font-semibold mb-1.5">Legend</p>
          <div className="flex flex-col gap-1">
            {Object.entries(GROUP_COLORS).map(([g, c]) =>
              nodes.some((n) => n.group === g) && (
                <div key={g} className="flex items-center gap-1.5 text-gray-400">
                  <span className="w-2 h-2 rounded-full border shrink-0" style={{ backgroundColor: c.background, borderColor: c.border }} />
                  {g}
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Side panel on node click */}
      {selected && selected.id && (
        <div className="absolute top-16 right-4 w-64 bg-gray-900/95 border border-gray-700 rounded-xl p-4 shadow-xl backdrop-blur-sm max-h-[70vh] overflow-y-auto pointer-events-auto">
          <button onClick={() => { networkRef.current?.unselectAll(); setSelected(null); }}
            className="absolute top-2 right-2 text-gray-500 hover:text-white text-sm w-6 h-6 flex items-center justify-center rounded hover:bg-gray-800 transition-colors">✕</button>
          <div className="w-full h-1 rounded-full mb-3" style={{ backgroundColor: (GROUP_COLORS[selected.group] || GROUP_COLORS.document).background }} />
          <h3 className="font-bold text-lg text-white mb-0.5 break-words">{selected.label}</h3>
          <p className="text-xs text-gray-500 mb-3">{selected.degree} connection{selected.degree !== 1 ? "s" : ""}</p>
          <div className="space-y-2 text-xs border-t border-gray-700 pt-3">
            {[
              { label: "Type", value: selected.type },
              { label: "Group", value: selected.group },
              { label: "ID", value: selected.id, mono: true },
            ].map((f) => (
              <div key={f.label}>
                <span className="text-gray-500 text-[10px] uppercase tracking-wider">{f.label}</span>
                <p className={`text-gray-300 ${f.mono ? "font-mono text-[11px] break-all" : ""}`}>{f.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {loading && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-gray-900/80 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-400 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          Loading…
        </div>
      )}
    </div>
  );
}
