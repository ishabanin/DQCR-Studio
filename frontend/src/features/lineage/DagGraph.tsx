import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Handle,
  NodeProps,
  NodeTypes,
  Position,
  ReactFlowInstance,
} from "reactflow";

import { LineageEdge, LineageNode } from "../../api/projects";
import { layoutGraph, toGraphEdges, toGraphNodes } from "./dagLayout";

export interface DagGraphHandle {
  fitView: () => void;
  resetView: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
}

type FolderNodeData = {
  id: string;
  name: string;
  materialized: string;
  queries: string[];
  className: string;
  onSelect: (nodeId: string) => void;
};

function FolderNode({ data }: NodeProps<FolderNodeData>) {
  return (
    <>
      <Handle className="lineage-handle" id="target-left" type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle className="lineage-handle" id="target-top" type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div
        className={data.className}
        onMouseDown={(event) => {
          event.stopPropagation();
        }}
        onClick={(event) => {
          event.stopPropagation();
          data.onSelect(data.id);
        }}
      >
        <div className="lg-node-head">
          <div className="lg-node-name">{data.name}</div>
          <span className="lg-node-mat">{data.materialized}</span>
        </div>
        <div className="lg-node-body">
          {data.queries.slice(0, 4).map((queryName) => (
            <span key={queryName} className="lg-sql-chip">
              <span className="lg-sql-chip-icon">f</span>
              {queryName}
            </span>
          ))}
          {data.queries.length > 4 ? <span className="lg-sql-chip-more">+{data.queries.length - 4}</span> : null}
        </div>
      </div>
      <Handle className="lineage-handle" id="source-right" type="source" position={Position.Right} style={{ opacity: 0 }} />
      <Handle className="lineage-handle" id="source-bottom" type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </>
  );
}

const nodeTypes: NodeTypes = {
  folderNode: FolderNode,
};

interface DagGraphProps {
  nodes: LineageNode[];
  edges: LineageEdge[];
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string) => void;
  layoutDirection: "LR" | "TB";
  compact: boolean;
  source: "framework_cli" | "fallback" | null;
}

const DagGraph = forwardRef<DagGraphHandle, DagGraphProps>(({
  nodes,
  edges,
  selectedNodeId,
  onNodeSelect,
  layoutDirection,
  compact,
  source,
}, ref) => {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance | null>(null);

  const graphData = useMemo(() => {
    const graphNodes = toGraphNodes(nodes, selectedNodeId, layoutDirection, compact, source, onNodeSelect);
    const graphEdges = toGraphEdges(edges, selectedNodeId, hoveredNodeId, source);
    return layoutGraph(graphNodes, graphEdges, layoutDirection);
  }, [nodes, edges, selectedNodeId, hoveredNodeId, layoutDirection, compact, source, onNodeSelect]);

  useEffect(() => {
    if (!flowInstance) return;
    const timer = window.setTimeout(() => {
      flowInstance.fitView({ padding: 0.15, duration: 300 });
    }, 0);

    return () => window.clearTimeout(timer);
  }, [flowInstance, graphData.nodes, graphData.edges]);

  useImperativeHandle(
    ref,
    () => ({
      fitView: () => flowInstance?.fitView({ padding: 0.15, duration: 300 }),
      resetView: () => flowInstance?.setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 }),
      zoomIn: () => flowInstance?.zoomIn({ duration: 200 }),
      zoomOut: () => flowInstance?.zoomOut({ duration: 200 }),
    }),
    [flowInstance],
  );

  return (
    <div className="lg-graph-surface">
      <ReactFlow
        nodes={graphData.nodes}
        edges={graphData.edges}
        nodeTypes={nodeTypes}
        style={{ width: "100%", height: "100%" }}
        minZoom={0.4}
        maxZoom={1.8}
        panOnDrag
        zoomOnScroll
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        onInit={setFlowInstance}
        onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
        onNodeMouseLeave={() => setHoveredNodeId(null)}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
      </ReactFlow>
    </div>
  );
});

DagGraph.displayName = "DagGraph";

export default DagGraph;
