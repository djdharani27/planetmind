import { useEffect, useRef, useState, useCallback } from "react";
import * as vis from "vis-network/standalone";
import "vis-network/styles/vis-network.css";
import { apiFetch } from "../lib/api";

/* ── Group definitions (color + shape per entity type) ── */
const GROUP_DEFS = {
  equipment: {
    color: { background: "#1e3a5f", border: "#60a5fa", highlight: { background: "#2563eb", border: "#93c5fd" }, hover: { background: "#1e40af", border: "#93c5fd" } },
    shape: "diamond", size: 30,
  },
  component: {
    color: { background: "#134e4a", border: "#2dd4bf", highlight: { background: "#115e59", border: "#5eead4" }, hover: { background: "#0d9488", border: "#5eead4" } },
    shape: "hexagon", size: 22,
  },
  failure: {
    color: { background: "#7f1d1d", border: "#f87171", highlight: { background: "#dc2626", border: "#fca5a5" }, hover: { background: "#991b1b", border: "#fca5a5" } },
    shape: "triangle", size: 26,
  },
  maintenanceactivity: {
    color: { background: "#78350f", border: "#fbbf24", highlight: { background: "#d97706", border: "#fde68a" }, hover: { background: "#92400e", border: "#fde68a" } },
    shape: "square", size: 22,
  },
  technician: {
    color: { background: "#064e3b", border: "#34d399", highlight: { background: "#059669", border: "#6ee7b7" }, hover: { background: "#065f46", border: "#6ee7b7" } },
    shape: "dot", size: 20,
  },
  regulation: {
    color: { background: "#3b0764", border: "#c084fc", highlight: { background: "#9333ea", border: "#d8b4fe" }, hover: { background: "#581c87", border: "#d8b4fe" } },
    shape: "star", size: 24,
  },
  document: {
    color: { background: "#1f2937", border: "#94a3b8", highlight: { background: "#475569", border: "#cbd5e1" }, hover: { background: "#334155", border: "#cbd5e1" } },
    shape: "box", size: 28,
  },
  location: {
    color: { background: "#713f12", border: "#fde047", highlight: { background: "#ca8a04", border: "#fef08a" }, hover: { background: "#854d0e", border: "#fef08a" } },
    shape: "ellipse", size: 24,
  },
  processparameter: {
    color: { background: "#831843", border: "#f472b6", highlight: { background: "#db2777", border: "#f9a8d4" }, hover: { background: "#78355d", border: "#f9a8d4" } },
    shape: "dot", size: 18,
  },
  date: {
    color: { background: "#2a4365", border: "#63b3ed", highlight: { background: "#2b6cb0", border: "#90cdf4" }, hover: { background: "#2a4365", border: "#90cdf4" } },
    shape: "box", size: 18,
  },
};

const GROUP_LABELS = {
  equipment: "Equipment",
  component: "Component",
  failure: "Failure",
  maintenanceactivity: "Maint. Activity",
  technician: "Technician",
  regulation: "Regulation",
  document: "Document",
  location: "Location",
  processparameter: "Process Param.",
  date: "Date",
};

/* ── Helpers ── */
function truncate(label, max = 35) {
  if (!label || label.length <= max) return label || "";
  return label.slice(0, max - 1) + "…";
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* ── Component ── */
export default function GraphPage() {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

  const loadGraph = useCallback(async (path) => {
    setLoading(true);
    setSelected(null);
    try {
      const data = await apiFetch(path);
      if (data.warning) {
        setSelected({ type: "warning", message: data.warning });
        setNodes([]);
        setEdges([]);
      } else {
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
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

  /* ── Build vis-network when nodes/edges change ── */
  useEffect(() => {
    if (!containerRef.current || !nodes.length) {
      networkRef.current?.destroy();
      networkRef.current = null;
      return;
    }
    networkRef.current?.destroy();

    const deg = {};
    for (const e of edges) {
      deg[e.from] = (deg[e.from] || 0) + 1;
      deg[e.to] = (deg[e.to] || 0) + 1;
    }
    const maxDeg = Math.max(...Object.values(deg), 1);

    const vNodes = new vis.DataSet(
      nodes.map((n) => {
        const g = n.group || "document";
        const d = deg[n.id] || 1;
        const def = GROUP_DEFS[g] || GROUP_DEFS.document;
        return {
          id: n.id,
          label: truncate(n.label),
          group: g,
          title: `<div style="font-size:13px;line-height:1.6;padding:4px;max-width:320px;word-wrap:break-word">
            <b style="color:${def.color.border}">${capitalize(g)}</b><br/>
            <span style="font-size:14px">${n.label}</span><br/>
            <span style="color:#9ca3af;font-size:11px">${d} connection${d !== 1 ? "s" : ""}</span>
          </div>`,
          value: d,
          size: Math.max(def.size || 20, 14 + (d / maxDeg) * 36),
          borderWidth: d > maxDeg * 0.6 ? 3 : 1.5,
          borderWidthSelected: 3,
          margin: { top: 6, bottom: 6, left: 6, right: 6 },
        };
      }),
    );

    const vEdges = new vis.DataSet(
      edges.map((e, i) => ({
        id: e.id || `e${i}`,
        from: e.from,
        to: e.to,
        label: e.label || "",
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        color: { color: "#64748b", highlight: "#818cf8", hover: "#818cf8", opacity: 0.85 },
        smooth: { type: "continuous", roundness: 0.2 },
        width: 1.2,
        font: { size: 9, color: "#94a3b8", strokeWidth: 2, strokeColor: "#0f172a", align: "middle" },
      })),
    );

    /* Build options with per-group coloring */
    const groups = {};
    for (const [key, def] of Object.entries(GROUP_DEFS)) {
      groups[key] = { color: def.color, shape: def.shape, font: { color: "#e2e8f0", size: 10, face: "Inter, system-ui, sans-serif", strokeWidth: 2, strokeColor: "#0f172a" } };
    }

    const options = {
      nodes: {
        font: { color: "#e2e8f0", size: 10, face: "Inter, system-ui, sans-serif", strokeWidth: 3, strokeColor: "#0f172a" },
        shadow: { enabled: true, color: "rgba(0,0,0,0.6)", size: 10, x: 0, y: 4 },
        borderWidth: 1.5,
        borderWidthSelected: 3,
        scaling: { min: 16, max: 60, label: { enabled: true, min: 8, max: 14 } },
      },
      edges: {
        width: 1.2,
        color: { color: "#64748b", highlight: "#818cf8", hover: "#818cf8", opacity: 0.85 },
        smooth: { type: "continuous", roundness: 0.2 },
        font: { size: 9, color: "#94a3b8", strokeWidth: 2, strokeColor: "#0f172a", align: "middle" },
      },
      groups,
      physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -25,
          centralGravity: 0.001,
          springLength: 400,
          springConstant: 0.004,
          damping: 0.92,
          avoidOverlap: 0.4,
        },
        stabilization: { iterations: 500, updateInterval: 25, fit: true },
        timestep: 0.3,
        adaptiveTimestep: true,
      },
      layout: { improvedLayout: true, hierarchical: { enabled: false } },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        keyboard: { enabled: true },
        zoomView: true,
        dragView: true,
        hoverConnectedEdges: true,
        selectConnectedEdges: true,
        hideEdgesOnDrag: false,
        hideEdgesOnZoom: false,
      },
    };

    const net = new vis.Network(containerRef.current, { nodes: vNodes, edges: vEdges }, options);

    /* Fit view once stabilization starts settling */
    net.once("stabilizationIterationsDone", () => {
      net.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });
    });

    net.on("selectNode", (p) => {
      const node = nodes.find((n) => n.id === p.nodes[0]);
      if (node) setSelected({ ...node, degree: deg[node.id] || 0, context: node.context, confidence: node.confidence });
    });
    net.on("deselectNode", () => setSelected(null));
    net.on("hoverNode", () => { document.body.style.cursor = "pointer"; });
    net.on("blurNode", () => { document.body.style.cursor = "default"; });

    networkRef.current = net;
  }, [nodes, edges]);

  const zoomIn = () => networkRef.current?.zoomIn(0.4);
  const zoomOut = () => networkRef.current?.zoomOut(0.4);
  const fitView = () => networkRef.current?.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });

  return (
    <div className="relative w-screen h-screen bg-gray-950 overflow-hidden">
      {/* Canvas */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* Empty state */}
      {!nodes.length && !loading && !selected?.type && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-gray-600 text-sm">No graph data available — upload and process documents first</p>
        </div>
      )}

      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-5 py-3 bg-gradient-to-b from-gray-950/90 to-transparent pointer-events-none">
        <div className="pointer-events-auto">
          <h1 className="text-lg font-bold text-white">Knowledge Graph</h1>
          {nodes.length > 0 && (
            <p className="text-xs text-gray-500">{nodes.length} entities · {edges.length} relationships</p>
          )}
        </div>
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={() => loadGraph("/graph")}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
          >
            {loading ? "…" : "Full Graph"}
          </button>
          <button
            onClick={() => setShowLegend((v) => !v)}
            className="bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg text-xs transition-colors"
          >
            Legend
          </button>
        </div>
      </div>

      {/* Legend */}
      {showLegend && (
        <div className="absolute top-16 left-4 bg-gray-900/95 border border-gray-700 rounded-xl px-4 py-3 text-xs shadow-xl backdrop-blur-sm z-10 pointer-events-auto max-h-[80vh] overflow-y-auto">
          <p className="text-gray-400 font-semibold mb-2">Legend</p>
          <div className="flex flex-col gap-1.5">
            {Object.entries(GROUP_DEFS).map(([key, def]) => {
              const count = nodes.filter((n) => n.group === key).length;
              if (!count) return null;
              return (
                <div key={key} className="flex items-center gap-2 text-gray-400">
                  <span
                    className="w-3 h-3 rounded-full border shrink-0"
                    style={{ backgroundColor: def.color.background, borderColor: def.color.border }}
                  />
                  <span>{GROUP_LABELS[key] || key}</span>
                  <span className="text-gray-600 ml-auto">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1 pointer-events-auto z-10">
        <button onClick={zoomIn} className="bg-gray-800 hover:bg-gray-700 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors" title="Zoom in">＋</button>
        <button onClick={zoomOut} className="bg-gray-800 hover:bg-gray-700 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors" title="Zoom out">−</button>
        <button onClick={fitView} className="bg-gray-800 hover:bg-gray-700 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors" title="Fit view">⊞</button>
      </div>

      {/* Detail panel */}
      {selected && selected.id && (
        <div className="absolute top-16 right-4 w-80 bg-gray-900/95 border border-gray-700 rounded-xl p-5 shadow-xl backdrop-blur-sm max-h-[75vh] overflow-y-auto pointer-events-auto z-10">
          <button
            onClick={() => { networkRef.current?.unselectAll(); setSelected(null); }}
            className="absolute top-2.5 right-2.5 text-gray-500 hover:text-white text-sm w-6 h-6 flex items-center justify-center rounded hover:bg-gray-800 transition-colors"
          >✕</button>

          {/* Header badge */}
          {(() => {
            const def = GROUP_DEFS[selected.group] || GROUP_DEFS.document;
            const gname = GROUP_LABELS[selected.group] || selected.group;
            return (
              <div className="flex items-center gap-2 mb-3">
                <span className="w-3 h-3 rounded-full border shrink-0"
                  style={{ backgroundColor: def.color.background, borderColor: def.color.border }} />
                <span className="text-xs text-gray-500 uppercase tracking-wider">{gname}</span>
                {selected.confidence != null && (
                  <span className="text-[10px] text-gray-600 ml-auto">{Math.round(selected.confidence * 100)}% confidence</span>
                )}
              </div>
            );
          })()}

          <h3 className="font-bold text-base text-white mb-3 break-words leading-snug">{selected.label}</h3>

          {/* Context text from the document */}
          {selected.context && (
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 mb-3">
              <span className="text-[10px] uppercase tracking-wider text-gray-500">Document context</span>
              <p className="text-gray-300 text-xs mt-1 leading-relaxed italic">{selected.context}</p>
            </div>
          )}

          <div className="space-y-3 text-xs border-t border-gray-700 pt-3">
            {/* Source document */}
            {(() => {
              const docEdges = edges.filter(e => e.from.startsWith("Document_") && e.to === selected.id);
              const srcDocIds = [...new Set(docEdges.map(e => e.from))];
              if (!srcDocIds.length) return null;
              return (
                <div>
                  <span className="text-gray-500 text-[10px] uppercase tracking-wider">Source document{srcDocIds.length > 1 ? "s" : ""}</span>
                  {srcDocIds.map(did => {
                    const dn = nodes.find(n => n.id === did);
                    return dn ? (
                      <p key={did} className="text-gray-300 mt-0.5 truncate">{dn.label}</p>
                    ) : null;
                  })}
                </div>
              );
            })()}

            {/* Connected neighbors */}
            {(() => {
              const neighborIds = new Set();
              for (const e of edges) {
                if (e.from === selected.id) neighborIds.add(e.to);
                if (e.to === selected.id) neighborIds.add(e.from);
              }
              neighborIds.delete(selected.id);

              const neighbors = [...neighborIds]
                .map(nid => nodes.find(n => n.id === nid))
                .filter(Boolean)
                .slice(0, 12);

              if (!neighbors.length) return null;

              // Group by type
              const grouped = {};
              for (const n of neighbors) {
                const g = n.group || "other";
                if (!grouped[g]) grouped[g] = [];
                grouped[g].push(n);
              }

              return (
                <div>
                  <span className="text-gray-500 text-[10px] uppercase tracking-wider">
                    Connected ({neighbors.length}{neighborIds.size > 12 ? "+" : ""})
                  </span>
                  <div className="space-y-1 mt-1">
                    {Object.entries(grouped).map(([gkey, ns]) => {
                      const def = GROUP_DEFS[gkey] || GROUP_DEFS.document;
                      return (
                        <div key={gkey}>
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="w-1.5 h-1.5 rounded-full shrink-0"
                              style={{ backgroundColor: def.color.background, borderColor: def.color.border }} />
                            <span className="text-[10px] text-gray-600">{GROUP_LABELS[gkey] || gkey}</span>
                          </div>
                          {ns.map(nw => (
                            <p key={nw.id} className="text-gray-400 text-xs ml-3 truncate">{nw.label}</p>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}

            <div>
              <span className="text-gray-500 text-[10px] uppercase tracking-wider">Value</span>
              <p className="font-mono text-[11px] text-gray-400 mt-0.5 break-all">{selected.label}</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-gray-900/80 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-400 flex items-center gap-2 pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          Loading graph…
        </div>
      )}

      {/* Warning/error */}
      {selected?.type === "warning" && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 bg-yellow-900/60 border border-yellow-700 rounded-lg px-4 py-2 text-xs text-yellow-300 backdrop-blur-sm pointer-events-none">
          {selected.message}
        </div>
      )}
      {selected?.type === "error" && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 bg-red-900/60 border border-red-700 rounded-lg px-4 py-2 text-xs text-red-300 backdrop-blur-sm pointer-events-none">
          {selected.message}
        </div>
      )}
    </div>
  );
}
