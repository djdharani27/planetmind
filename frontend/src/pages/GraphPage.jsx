import { useEffect, useRef, useState } from "react";
import * as vis from "vis-network/standalone";
import "vis-network/styles/vis-network.css";
import { apiFetch } from "../lib/api";

const GROUP_COLORS = {
  equipment: { border: "#3b82f6", background: "#1e3a5f", highlight: "#60a5fa" },
  component: { border: "#06b6d4", background: "#164e63", highlight: "#22d3ee" },
  failure: { border: "#ef4444", background: "#5f1a1a", highlight: "#f87171" },
  maintenanceactivity: { border: "#f59e0b", background: "#5c3d0a", highlight: "#fbbf24" },
  technician: { border: "#10b981", background: "#064e3b", highlight: "#34d399" },
  regulation: { border: "#a855f7", background: "#3b1a6e", highlight: "#c084fc" },
  document: { border: "#6b7280", background: "#1f2937", highlight: "#9ca3af" },
  location: { border: "#ecc94b", background: "#5c4a0a", highlight: "#fef08a" },
  processparameter: { border: "#ec4899", background: "#5c1442", highlight: "#f472b6" },
};

export default function GraphPage() {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [docId, setDocId] = useState("");
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadGraph = async (path) => {
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
  };

  useEffect(() => {
    // Load overview on mount
    loadGraph("/graph");

    return () => {
      if (networkRef.current) networkRef.current.destroy();
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return;

    if (networkRef.current) networkRef.current.destroy();

    const graphNodes = new vis.DataSet(
      nodes.map((n) => ({
        id: n.id,
        label: n.label,
        group: n.group,
        title: `<b>${n.type}</b><br/>${n.label}`,
        value: 2,
      }))
    );

    const graphEdges = new vis.DataSet(
      edges.map((e) => ({
        id: e.id || `${e.from}-${e.to}-${e.label}`,
        from: e.from,
        to: e.to,
        label: e.label,
        arrows: "to",
        font: { size: 10, color: "#9ca3af", strokeWidth: 0 },
        color: { color: "#4b5563", highlight: "#6b7280" },
        smooth: { type: "curvedCW", roundness: 0.2 },
      }))
    );

    const options = {
      nodes: {
        shape: "dot",
        size: 25,
        font: { size: 12, color: "#d1d5db", face: "Inter" },
        borderWidth: 2,
        shadow: { enabled: true, size: 8 },
      },
      edges: {
        width: 1.5,
        selectionWidth: 2,
      },
      groups: GROUP_COLORS,
      physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -35,
          centralGravity: 0.01,
          springLength: 120,
          springConstant: 0.08,
        },
        stabilization: { iterations: 150 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
      },
    };

    const network = new vis.Network(containerRef.current, { nodes: graphNodes, edges: graphEdges }, options);
    networkRef.current = network;

    network.on("selectNode", (params) => {
      const nodeId = params.nodes[0];
      const node = nodes.find((n) => n.id === nodeId);
      setSelected(node || null);
    });

    network.on("deselectNode", () => setSelected(null));
  }, [nodes, edges]);

  const loadForDoc = () => {
    if (!docId.trim()) return;
    loadGraph(`/graph/${docId.trim()}`);
  };

  return (
    <div className="p-4 md:p-6 max-w-full mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-2">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Knowledge Graph</h1>
          <p className="text-gray-400 text-sm">Interactive graph of entities, equipment, failures, and relationships</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => loadGraph("/graph")}
            className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm"
          >
            Full Graph
          </button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-2 mb-4">
        <input
          value={docId}
          onChange={(e) => setDocId(e.target.value)}
          placeholder="Document ID to view its graph"
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm"
        />
        <button
          onClick={loadForDoc}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm"
        >
          {loading ? "Loading..." : "View"}
        </button>
      </div>

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

      <div className="flex flex-col lg:flex-row gap-4">
        <div
          ref={containerRef}
          className="flex-1 bg-gray-900 rounded-xl border border-gray-800"
          style={{ minHeight: "500px", height: "70vh" }}
        />

        {selected && selected.id && (
          <div className="lg:w-72 bg-gray-900 rounded-xl border border-gray-800 p-4">
            <h3 className="font-bold text-lg mb-2">{selected.label}</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-gray-500 text-xs uppercase">Type</span>
                <p>{selected.type}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs uppercase">ID</span>
                <p className="text-xs font-mono text-gray-400 break-all">{selected.id}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs uppercase">Group</span>
                <p className="capitalize">{selected.group}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {Object.entries(GROUP_COLORS).map(([group, colors]) => (
          <div key={group} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span
              className="w-3 h-3 rounded-full border"
              style={{ backgroundColor: colors.background, borderColor: colors.border }}
            />
            {group}
          </div>
        ))}
      </div>
    </div>
  );
}
