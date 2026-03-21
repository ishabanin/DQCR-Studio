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
  const onNodeSelect = () => undefined;

  it("maps edge status to color", () => {
    expect(edgeColor("warn")).toBe("#EF9F27");
    expect(edgeColor("error")).toBe("#E24B4A");
    expect(edgeColor("resolved")).toBe("#B4B2A9");
  });

  it("creates reactflow nodes and edges", () => {
    const nodes = toGraphNodes(NODES, "a", "LR", false, "framework_cli", onNodeSelect);
    const edges = toGraphEdges(EDGES, "a", null, "framework_cli");
    expect(nodes).toHaveLength(2);
    expect(edges).toHaveLength(1);
    expect(nodes[0].data.className).toContain("selected");
    expect(edges[0].style?.stroke).toBe("#1D9E75");
  });

  it("applies dagre layout positions", () => {
    const nodes = toGraphNodes(NODES, null, "TB", true, "fallback", onNodeSelect);
    const edges = toGraphEdges(EDGES, null, null, "fallback");
    const result = layoutGraph(nodes, edges, "TB");
    expect(result.nodes).toHaveLength(2);
    expect(result.nodes[0].position.y).toBeLessThan(result.nodes[1].position.y);
  });
});
