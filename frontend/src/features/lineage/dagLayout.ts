import dagre from "dagre";
import { Edge, MarkerType, Node, Position } from "reactflow";

import { LineageEdge, LineageNode } from "../../api/projects";

export const NODE_WIDTH = 260;
export const NODE_HEIGHT = 96;

export function edgeColor(status: string): string {
  if (status === "active") return "#1D9E75";
  if (status === "fallback" || status === "warn") return "#EF9F27";
  if (status === "error") return "#E24B4A";
  return "#B4B2A9";
}

export function layoutGraph(nodes: Node[], edges: Edge[], direction: "LR" | "TB"): { nodes: Node[]; edges: Edge[] } {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({ rankdir: direction, ranksep: 80, nodesep: 30 });
  graph.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => {
    const width = typeof node.style?.width === "number" ? node.style.width : NODE_WIDTH;
    const height = typeof node.style?.height === "number" ? node.style.height : NODE_HEIGHT;
    graph.setNode(node.id, { width, height });
  });
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  const positionedNodes = nodes.map((node) => {
    const point = graph.node(node.id);
    const width = typeof node.style?.width === "number" ? node.style.width : NODE_WIDTH;
    const height = typeof node.style?.height === "number" ? node.style.height : NODE_HEIGHT;
    return {
      ...node,
      position: {
        x: point.x - width / 2,
        y: point.y - height / 2,
      },
    };
  });

  return { nodes: positionedNodes, edges };
}

export function toGraphNodes(
  nodes: LineageNode[],
  selectedNodeId: string | null,
  direction: "LR" | "TB",
  compact: boolean,
  source: "framework_cli" | "fallback" | null,
  onNodeSelect: (nodeId: string) => void,
): Node[] {
  const nodeWidth = compact ? 180 : NODE_WIDTH;
  const nodeHeight = compact ? 56 : NODE_HEIGHT;

  return nodes.map((node) => ({
    id: node.id,
    type: "folderNode",
    position: { x: 0, y: 0 },
    data: {
      id: node.id,
      name: node.name,
      materialized: node.materialized,
      queries: node.queries,
      className: buildNodeClassName(node, selectedNodeId, compact, source),
      onSelect: onNodeSelect,
    },
    draggable: false,
    sourcePosition: direction === "TB" ? Position.Bottom : Position.Right,
    targetPosition: direction === "TB" ? Position.Top : Position.Left,
    style: { width: nodeWidth, height: nodeHeight, padding: 0, border: "none", background: "transparent" },
  }));
}

function buildNodeClassName(
  node: LineageNode,
  selectedNodeId: string | null,
  compact: boolean,
  source: "framework_cli" | "fallback" | null,
): string {
  const classes = ["lg-node", "nopan", "nodrag"];
  const normalizedMaterialized = String(node.materialized || "").toLowerCase();
  if (["flags", "pre", "params", "sql", "post"].includes(normalizedMaterialized)) {
    classes.push(`lg-node-scope-${normalizedMaterialized}`);
  }
  if (node.id === selectedNodeId) classes.push("selected");
  if (source === "fallback") classes.push("stale");
  if (compact) classes.push("compact");
  return classes.join(" ");
}

function resolveEdgeStatus(
  edge: LineageEdge,
  selectedNodeId: string | null,
  hoveredNodeId: string | null,
  source: "framework_cli" | "fallback" | null,
): "normal" | "active" | "fallback" | "error" {
  const activeNodeId = hoveredNodeId ?? selectedNodeId;
  if (edge.status === "error") return "error";
  if (activeNodeId && (edge.source === activeNodeId || edge.target === activeNodeId)) return "active";
  if (source === "fallback" || edge.status === "warn" || edge.status === "fallback") return "fallback";
  return "normal";
}

export function toGraphEdges(
  edges: LineageEdge[],
  selectedNodeId: string | null,
  hoveredNodeId: string | null,
  source: "framework_cli" | "fallback" | null,
): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    animated: false,
    data: { status: edge.status },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: edgeColor(resolveEdgeStatus(edge, selectedNodeId, hoveredNodeId, source)),
    },
    style: {
      stroke: edgeColor(resolveEdgeStatus(edge, selectedNodeId, hoveredNodeId, source)),
      strokeWidth: 1.5,
      opacity:
        hoveredNodeId && edge.source !== hoveredNodeId && edge.target !== hoveredNodeId
          ? 0.25
          : 1,
    },
  }));
}
