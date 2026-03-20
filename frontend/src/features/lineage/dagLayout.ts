import dagre from "dagre";
import { Edge, MarkerType, Node, Position } from "reactflow";

import { LineageEdge, LineageNode } from "../../api/projects";

export const NODE_WIDTH = 260;
export const NODE_HEIGHT = 96;

export function edgeColor(status: string): string {
  if (status === "warn") return "#f59e0b";
  if (status === "error") return "#ef4444";
  return "#64748b";
}

export function layoutGraph(nodes: Node[], edges: Edge[], direction: "LR" | "TB"): { nodes: Node[]; edges: Edge[] } {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({ rankdir: direction, ranksep: 80, nodesep: 30 });
  graph.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  const positionedNodes = nodes.map((node) => {
    const point = graph.node(node.id);
    return {
      ...node,
      position: {
        x: point.x - NODE_WIDTH / 2,
        y: point.y - NODE_HEIGHT / 2,
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
): Node[] {
  return nodes.map((node) => ({
    id: node.id,
    type: "folderNode",
    position: { x: 0, y: 0 },
    data: {
      id: node.id,
      name: node.name,
      materialized: node.materialized,
      queries: node.queries,
      selected: selectedNodeId === node.id,
      compact,
    },
    draggable: false,
    sourcePosition: direction === "TB" ? Position.Bottom : Position.Right,
    targetPosition: direction === "TB" ? Position.Top : Position.Left,
    style: { width: compact ? 180 : NODE_WIDTH, padding: 0, border: "none", background: "transparent" },
  }));
}

export function toGraphEdges(edges: LineageEdge[]): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    animated: false,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: edgeColor(edge.status),
    },
    style: {
      stroke: edgeColor(edge.status),
      strokeWidth: 1.6,
    },
  }));
}

