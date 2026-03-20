import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  NodeProps,
  NodeTypes,
  Position,
} from "reactflow";

import { LineageEdge, LineageNode } from "../../api/projects";
import { layoutGraph, toGraphEdges, toGraphNodes } from "./dagLayout";

type FolderNodeData = {
  id: string;
  name: string;
  materialized: string;
  queries: string[];
  selected: boolean;
  compact: boolean;
};

function FolderNode({ data }: NodeProps<FolderNodeData>) {
  if (data.compact) {
    return (
      <>
        <Handle className="lineage-handle" id="target-left" type="target" position={Position.Left} />
        <Handle className="lineage-handle" id="target-top" type="target" position={Position.Top} />
        <div
          className={
            data.selected
              ? "lineage-folder-node lineage-folder-node-compact lineage-folder-node-selected"
              : "lineage-folder-node lineage-folder-node-compact"
          }
        >
          <strong>{data.name}</strong>
        </div>
        <Handle className="lineage-handle" id="source-right" type="source" position={Position.Right} />
        <Handle className="lineage-handle" id="source-bottom" type="source" position={Position.Bottom} />
      </>
    );
  }

  return (
    <>
      <Handle className="lineage-handle" id="target-left" type="target" position={Position.Left} />
      <Handle className="lineage-handle" id="target-top" type="target" position={Position.Top} />
      <div className={data.selected ? "lineage-folder-node lineage-folder-node-selected" : "lineage-folder-node"}>
        <div className="lineage-rf-head">
          <strong>{data.name}</strong>
          <span className="lineage-materialized">{data.materialized}</span>
        </div>
        <div className="lineage-chip-list">
          {data.queries.slice(0, 4).map((queryName) => (
            <span key={queryName} className="lineage-sql-chip">
              {queryName}
            </span>
          ))}
          {data.queries.length > 4 ? <span className="lineage-sql-chip">+{data.queries.length - 4}</span> : null}
        </div>
      </div>
      <Handle className="lineage-handle" id="source-right" type="source" position={Position.Right} />
      <Handle className="lineage-handle" id="source-bottom" type="source" position={Position.Bottom} />
    </>
  );
}

const nodeTypes: NodeTypes = {
  folderNode: FolderNode,
};

export default function DagGraph({
  nodes,
  edges,
  selectedNodeId,
  onNodeSelect,
  layoutDirection,
  compact,
}: {
  nodes: LineageNode[];
  edges: LineageEdge[];
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string) => void;
  layoutDirection: "LR" | "TB";
  compact: boolean;
}) {
  const graphData = useMemo(() => {
    const graphNodes = toGraphNodes(nodes, selectedNodeId, layoutDirection, compact);
    const graphEdges = toGraphEdges(edges);
    return layoutGraph(graphNodes, graphEdges, layoutDirection);
  }, [nodes, edges, selectedNodeId, layoutDirection, compact]);

  return (
    <div className="lineage-canvas">
      <ReactFlow
        nodes={graphData.nodes}
        edges={graphData.edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.4}
        maxZoom={1.8}
        panOnDrag
        zoomOnScroll
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        onNodeClick={(_, node) => onNodeSelect(node.id)}
      >
        <Background gap={14} size={1} color="#d1d9e6" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
