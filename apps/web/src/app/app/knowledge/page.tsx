"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Network,
  RefreshCw,
  Loader2,
  GitPullRequest,
  FileText,
  MessageSquare,
  Ticket,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Info,
} from "lucide-react";
import {
  knowledgeGraph,
  type GraphNode,
  type GraphEdge,
  type KnowledgeGraph,
  type GraphStats,
} from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoKnowledgeGraph, demoGraphStats } from "@/lib/demo-data";

/* ── Colour / icon maps ── */

const TYPE_COLORS: Record<string, string> = {
  ticket: "#f59e0b",
  pull_request: "#10b981",
  page: "#6366f1",
  message: "#ec4899",
  commit: "#8b5cf6",
  issue: "#ef4444",
};

const RELATION_COLORS: Record<string, string> = {
  mentions: "#60a5fa",
  related_to: "#a78bfa",
  same_sprint: "#34d399",
  same_label: "#fbbf24",
  blocks: "#f87171",
  comment_on: "#94a3b8",
  authored_by: "#c084fc",
};

function typeIcon(t: string) {
  switch (t) {
    case "pull_request":
      return GitPullRequest;
    case "page":
      return FileText;
    case "message":
      return MessageSquare;
    default:
      return Ticket;
  }
}

/* ── Force simulation types ── */

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx: number | null;
  fy: number | null;
}

/* ── Minimal force-directed layout (no external deps) ── */

function initSimulation(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
): { nodes: SimNode[]; edges: GraphEdge[] } {
  const simNodes: SimNode[] = nodes.map((n, i) => ({
    ...n,
    x: width / 2 + (Math.random() - 0.5) * width * 0.6,
    y: height / 2 + (Math.random() - 0.5) * height * 0.6,
    vx: 0,
    vy: 0,
    fx: null,
    fy: null,
  }));
  return { nodes: simNodes, edges };
}

function tick(simNodes: SimNode[], edges: GraphEdge[], width: number, height: number) {
  const alpha = 0.3;
  const repulsion = 3000;
  const attraction = 0.005;
  const centerGravity = 0.01;
  const damping = 0.85;
  const idealLength = 150;

  // Node-to-node repulsion
  for (let i = 0; i < simNodes.length; i++) {
    for (let j = i + 1; j < simNodes.length; j++) {
      const a = simNodes[i];
      const b = simNodes[j];
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (repulsion / (dist * dist)) * alpha;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      if (a.fx === null) { a.vx += dx; a.vy += dy; }
      if (b.fx === null) { b.vx -= dx; b.vy -= dy; }
    }
  }

  // Edge attraction
  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
  for (const e of edges) {
    const a = nodeMap.get(e.source);
    const b = nodeMap.get(e.target);
    if (!a || !b) continue;
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = (dist - idealLength) * attraction * alpha;
    dx = (dx / dist) * force;
    dy = (dy / dist) * force;
    if (a.fx === null) { a.vx += dx; a.vy += dy; }
    if (b.fx === null) { b.vx -= dx; b.vy -= dy; }
  }

  // Center gravity
  const cx = width / 2;
  const cy = height / 2;
  for (const n of simNodes) {
    if (n.fx !== null) continue;
    n.vx += (cx - n.x) * centerGravity * alpha;
    n.vy += (cy - n.y) * centerGravity * alpha;
  }

  // Apply velocity
  for (const n of simNodes) {
    if (n.fx !== null) {
      n.x = n.fx;
      n.y = n.fy!;
      n.vx = 0;
      n.vy = 0;
      continue;
    }
    n.vx *= damping;
    n.vy *= damping;
    n.x += n.vx;
    n.y += n.vy;
    // Keep in bounds with padding
    n.x = Math.max(40, Math.min(width - 40, n.x));
    n.y = Math.max(40, Math.min(height - 40, n.y));
  }
}

/* ── Canvas renderer ── */

function drawGraph(
  ctx: CanvasRenderingContext2D,
  simNodes: SimNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
  zoom: number,
  panX: number,
  panY: number,
  selectedId: string | null,
  hoveredId: string | null,
) {
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(zoom, zoom);

  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

  // Draw edges
  for (const e of edges) {
    const a = nodeMap.get(e.source);
    const b = nodeMap.get(e.target);
    if (!a || !b) continue;

    const highlighted =
      selectedId !== null && (e.source === selectedId || e.target === selectedId);

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = highlighted
      ? RELATION_COLORS[e.relation_type] || "#60a5fa"
      : "rgba(255,255,255,0.08)";
    ctx.lineWidth = highlighted ? 2 : 1;
    ctx.stroke();

    // Relation label on highlighted edges
    if (highlighted) {
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      ctx.font = "10px sans-serif";
      ctx.fillStyle = "rgba(255,255,255,0.5)";
      ctx.textAlign = "center";
      ctx.fillText(e.relation_type.replace("_", " "), mx, my - 4);
    }
  }

  // Draw nodes
  for (const n of simNodes) {
    const isSelected = n.id === selectedId;
    const isHovered = n.id === hoveredId;
    const isNeighborOfSelected =
      selectedId !== null &&
      edges.some(
        (e) =>
          (e.source === selectedId && e.target === n.id) ||
          (e.target === selectedId && e.source === n.id),
      );

    const col = TYPE_COLORS[n.entity_type] || "#6b7280";
    const radius = isSelected ? 14 : isHovered ? 12 : 10;
    const opacity =
      selectedId === null || isSelected || isNeighborOfSelected ? 1 : 0.25;

    ctx.globalAlpha = opacity;

    // Glow
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, radius + 6, 0, Math.PI * 2);
      ctx.fillStyle = col + "30";
      ctx.fill();
    }

    // Circle
    ctx.beginPath();
    ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = col;
    ctx.fill();
    ctx.strokeStyle = isSelected ? "#fff" : "rgba(0,0,0,0.3)";
    ctx.lineWidth = isSelected ? 2 : 1;
    ctx.stroke();

    // Label
    ctx.font = `${isSelected ? "bold " : ""}11px sans-serif`;
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.textAlign = "center";
    const label =
      n.title.length > 30 ? n.title.slice(0, 28) + "…" : n.title;
    ctx.fillText(label, n.x, n.y + radius + 14);

    ctx.globalAlpha = 1;
  }

  ctx.restore();
}

/* ── Hit-test helper ── */

function hitTest(
  simNodes: SimNode[],
  mx: number,
  my: number,
  zoom: number,
  panX: number,
  panY: number,
): SimNode | null {
  const wx = (mx - panX) / zoom;
  const wy = (my - panY) / zoom;
  for (let i = simNodes.length - 1; i >= 0; i--) {
    const n = simNodes[i];
    const dx = wx - n.x;
    const dy = wy - n.y;
    if (dx * dx + dy * dy < 14 * 14) return n;
  }
  return null;
}

/* ── Stat badge ── */

function Badge({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5">
      <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-xs font-semibold text-white ml-auto">{value}</span>
    </div>
  );
}

/* ── Main page component ── */

export default function KnowledgePage() {
  const { isDemo } = useDemo();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const simRef = useRef<{ nodes: SimNode[]; edges: GraphEdge[] } | null>(null);

  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const [zoom, setZoom] = useState(1);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const isPanning = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });
  const dragNode = useRef<SimNode | null>(null);

  /* ── Fetch data ── */

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (isDemo) {
        setGraph(demoKnowledgeGraph);
        setStats(demoGraphStats);
      } else {
        const [g, s] = await Promise.all([
          knowledgeGraph.getGraph(),
          knowledgeGraph.stats(),
        ]);
        setGraph(g);
        setStats(s);
      }
    } catch {
      setGraph(demoKnowledgeGraph);
      setStats(demoGraphStats);
    } finally {
      setLoading(false);
    }
  }, [isDemo]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ── Rebuild ── */

  const handleRebuild = async () => {
    if (isDemo) return;
    setRebuilding(true);
    try {
      await knowledgeGraph.rebuild();
      await fetchData();
    } finally {
      setRebuilding(false);
    }
  };

  /* ── Initialize and run simulation ── */

  useEffect(() => {
    if (!graph || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.parentElement!.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = rect.width;
    const h = rect.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);

    const sim = initSimulation(graph.nodes, graph.edges, w, h);
    simRef.current = sim;

    let tickCount = 0;
    const maxTicks = 300;

    function animate() {
      if (!simRef.current) return;
      if (tickCount < maxTicks) {
        tick(simRef.current.nodes, simRef.current.edges, w, h);
        tickCount++;
      }
      const ctx2 = canvas.getContext("2d")!;
      ctx2.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawGraph(
        ctx2,
        simRef.current.nodes,
        simRef.current.edges,
        w,
        h,
        zoom,
        panX,
        panY,
        selectedNode?.id ?? null,
        hoveredId,
      );
      animRef.current = requestAnimationFrame(animate);
    }

    animate();

    return () => cancelAnimationFrame(animRef.current);
  }, [graph, zoom, panX, panY, selectedNode, hoveredId]);

  /* ── Canvas interactions ── */

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!simRef.current) return;
      const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const hit = hitTest(simRef.current.nodes, mx, my, zoom, panX, panY);
      if (hit) {
        dragNode.current = hit;
        hit.fx = hit.x;
        hit.fy = hit.y;
        setSelectedNode(hit);
      } else {
        isPanning.current = true;
        setSelectedNode(null);
      }
      lastMouse.current = { x: e.clientX, y: e.clientY };
    },
    [zoom, panX, panY],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const dx = e.clientX - lastMouse.current.x;
      const dy = e.clientY - lastMouse.current.y;
      lastMouse.current = { x: e.clientX, y: e.clientY };

      if (dragNode.current) {
        dragNode.current.fx = (dragNode.current.fx ?? dragNode.current.x) + dx / zoom;
        dragNode.current.fy = (dragNode.current.fy ?? dragNode.current.y) + dy / zoom;
        return;
      }

      if (isPanning.current) {
        setPanX((p) => p + dx);
        setPanY((p) => p + dy);
        return;
      }

      // Hover detection
      if (!simRef.current) return;
      const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const hit = hitTest(simRef.current.nodes, mx, my, zoom, panX, panY);
      setHoveredId(hit?.id ?? null);
    },
    [zoom, panX, panY],
  );

  const handleMouseUp = useCallback(() => {
    if (dragNode.current) {
      dragNode.current.fx = null;
      dragNode.current.fy = null;
      dragNode.current = null;
    }
    isPanning.current = false;
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.2, Math.min(3, z - e.deltaY * 0.001)));
  }, []);

  /* ── Neighbor edges of selected node ── */

  const neighborEdges = selectedNode
    ? (graph?.edges ?? []).filter(
        (e) => e.source === selectedNode.id || e.target === selectedNode.id,
      )
    : [];
  const neighborNodes = selectedNode
    ? (simRef.current?.nodes ?? []).filter((n) =>
        neighborEdges.some(
          (e) =>
            (e.source === selectedNode.id && e.target === n.id) ||
            (e.target === selectedNode.id && e.source === n.id),
        ),
      )
    : [];

  /* ── Render ── */

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-4 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Network className="w-6 h-6 text-[var(--accent)]" />
            Knowledge Graph
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Explore relationships between your engineering artifacts across integrations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setZoom(1); setPanX(0); setPanY(0); }}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Reset view"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.min(3, z + 0.2))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.2, z - 0.2))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleRebuild}
            disabled={rebuilding || isDemo}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent)]/20 text-[var(--accent)] hover:bg-[var(--accent)]/30 transition-colors disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${rebuilding ? "animate-spin" : ""}`} />
            {rebuilding ? "Rebuilding…" : "Rebuild Graph"}
          </button>
        </div>
      </div>

      {/* Body: graph canvas + side panel */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Canvas */}
        <div className="flex-1 glass-card relative overflow-hidden">
          <canvas
            ref={canvasRef}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          />
          {/* Legend overlay */}
          <div className="absolute bottom-3 left-3 flex flex-wrap gap-2">
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <div
                key={type}
                className="flex items-center gap-1.5 px-2 py-1 rounded bg-black/60 backdrop-blur text-xs text-gray-300"
              >
                <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                {type.replace("_", " ")}
              </div>
            ))}
          </div>
          {!graph?.nodes.length && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500">
              <Network className="w-12 h-12 mb-2 opacity-30" />
              <p className="text-sm">No graph data yet. Sync integrations to build the knowledge graph.</p>
            </div>
          )}
        </div>

        {/* Side panel */}
        <div className="w-80 flex flex-col gap-4 shrink-0">
          {/* Stats */}
          {stats && (
            <div className="glass-card p-4 space-y-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Info className="w-4 h-4 text-gray-400" />
                Graph Statistics
              </h2>

              <div className="grid grid-cols-2 gap-2">
                <div className="text-center p-2 rounded-lg bg-white/5">
                  <div className="text-xl font-bold text-white">{stats.total_nodes}</div>
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Nodes</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-white/5">
                  <div className="text-xl font-bold text-white">{stats.total_edges}</div>
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Edges</div>
                </div>
              </div>

              <div className="space-y-1.5">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">By Type</p>
                {Object.entries(stats.nodes_by_type).map(([t, v]) => (
                  <Badge key={t} label={t.replace("_", " ")} value={v} color={TYPE_COLORS[t] || "#6b7280"} />
                ))}
              </div>

              <div className="space-y-1.5">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">By Relation</p>
                {Object.entries(stats.edges_by_relation).map(([r, v]) => (
                  <Badge key={r} label={r.replace("_", " ")} value={v} color={RELATION_COLORS[r] || "#6b7280"} />
                ))}
              </div>

              <div className="space-y-1.5">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">By Source</p>
                {Object.entries(stats.nodes_by_source).map(([s, v]) => (
                  <Badge key={s} label={s} value={v} color="#60a5fa" />
                ))}
              </div>
            </div>
          )}

          {/* Selected node detail */}
          {selectedNode && (
            <div className="glass-card p-4 space-y-3">
              <div className="flex items-start gap-3">
                {(() => {
                  const Icon = typeIcon(selectedNode.entity_type);
                  return (
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                      style={{ background: (TYPE_COLORS[selectedNode.entity_type] || "#6b7280") + "30" }}
                    >
                      <Icon className="w-4 h-4" style={{ color: TYPE_COLORS[selectedNode.entity_type] }} />
                    </div>
                  );
                })()}
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-white leading-snug">{selectedNode.title}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {selectedNode.entity_type.replace("_", " ")} · {selectedNode.source_integration}
                  </p>
                </div>
              </div>

              <p className="text-xs text-gray-400 leading-relaxed">
                {selectedNode.content_preview}
              </p>

              {selectedNode.source_url && (
                <a
                  href={selectedNode.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-[var(--accent)] hover:underline"
                >
                  <ExternalLink className="w-3 h-3" />
                  Open in {selectedNode.source_integration}
                </a>
              )}

              {neighborNodes.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-white/5">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">
                    Connected ({neighborNodes.length})
                  </p>
                  {neighborNodes.map((n) => {
                    const edge = neighborEdges.find(
                      (e) =>
                        (e.source === selectedNode.id && e.target === n.id) ||
                        (e.target === selectedNode.id && e.source === n.id),
                    );
                    return (
                      <button
                        key={n.id}
                        onClick={() => setSelectedNode(n)}
                        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-left transition-colors"
                      >
                        <div
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ background: TYPE_COLORS[n.entity_type] || "#6b7280" }}
                        />
                        <span className="text-xs text-white truncate flex-1">{n.title}</span>
                        {edge && (
                          <span className="text-[10px] text-gray-500 shrink-0">
                            {edge.relation_type.replace("_", " ")}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {!selectedNode && (
            <div className="glass-card p-4 flex flex-col items-center justify-center text-gray-500 text-xs gap-2">
              <Info className="w-5 h-5 opacity-40" />
              Click a node to see details and connections
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
