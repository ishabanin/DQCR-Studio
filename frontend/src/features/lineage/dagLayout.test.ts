import { describe, expect, it } from "vitest";

import type { LineageEdge, LineageNode } from "../../api/projects";
import { edgeColor, layoutGraph, toGraphEdges, toGraphNodes } from "./dagLayout";

const NODES: LineageNode[] = [
  {
    id: "a",
    name: "A",
    path: "model/SampleModel/workflow/a",
    materialized: "insert_fc",
    enabled_contexts: ["default"],
    queries: ["001_a.sql"],
    parameters: [],
    ctes: [],
  },
  {
    id: "b",
    name: "B",
    path: "model/SampleModel/workflow/b",
    materialized: "insert_fc",
    enabled_contexts: ["default"],
    queries: ["001_b.sql"],
    parameters: [],
    ctes: [],
  },
];

const EDGES: LineageEdge[] = [{ id: "a->b", source: "a", target: "b", status: "resolved" }];

describe("dagLayout", () => {
  it("maps edge status to color", () => {
    expect(edgeColor("warn")).toBe("#f59e0b");
    expect(edgeColor("error")).toBe("#ef4444");
    expect(edgeColor("resolved")).toBe("#64748b");
  });

  it("creates reactflow nodes and edges", () => {
    const nodes = toGraphNodes(NODES, "a", "LR", false);
    const edges = toGraphEdges(EDGES);
    expect(nodes).toHaveLength(2);
    expect(edges).toHaveLength(1);
    expect(nodes[0].data.selected).toBe(true);
    expect(edges[0].style?.stroke).toBe("#64748b");
  });

  it("applies dagre layout positions", () => {
    const nodes = toGraphNodes(NODES, null, "TB", true);
    const edges = toGraphEdges(EDGES);
    const result = layoutGraph(nodes, edges, "TB");
    expect(result.nodes).toHaveLength(2);
    expect(result.nodes[0].position.y).toBeLessThan(result.nodes[1].position.y);
  });
});
