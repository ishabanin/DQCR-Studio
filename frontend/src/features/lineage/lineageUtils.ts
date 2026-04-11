import { LineageNode } from "../../api/projects";

export interface SearchableNode {
  id: string;
  name: string;
  path: string;
  queries: string[];
  parameters: string[];
}

export function nodeMatchesSearch(node: SearchableNode, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;

  return (
    node.name.toLowerCase().includes(normalized) ||
    node.path.toLowerCase().includes(normalized) ||
    node.queries.some((queryName) => queryName.toLowerCase().includes(normalized)) ||
    node.parameters.some((parameter) => parameter.toLowerCase().includes(normalized))
  );
}

export function computeVisibleNodes(
  nodes: SearchableNode[],
  searchQuery: string,
  activeContexts: string[],
  enabledContextsMap: Record<string, string[] | null>,
): Set<string> {
  const visible = new Set<string>();

  for (const node of nodes) {
    const enabledContexts = enabledContextsMap[node.id];
    if (enabledContexts !== null && enabledContexts !== undefined && activeContexts.length > 0) {
      const hasMatch = activeContexts.some((contextId) => enabledContexts.includes(contextId));
      if (!hasMatch) continue;
    }

    if (!nodeMatchesSearch(node, searchQuery)) continue;
    visible.add(node.id);
  }

  return visible;
}

export function formatNodePath(rawPath: string, modelId: string): string {
  const workflowMarker = `model/${modelId}/workflow/`;
  const modelMarker = `models/${modelId}/workflow/`;
  const workflowIndex = rawPath.indexOf(workflowMarker);
  if (workflowIndex !== -1) {
    return rawPath.slice(workflowIndex);
  }

  const modelsIndex = rawPath.indexOf(modelMarker);
  if (modelsIndex !== -1) {
    return rawPath.slice(modelsIndex);
  }

  return rawPath;
}

export function getConnectionCounts(
  nodeId: string | null,
  edges: Array<{ source: string; target: string }>,
): { inbound: number; outbound: number } {
  if (!nodeId) return { inbound: 0, outbound: 0 };

  return {
    inbound: edges.filter((edge) => edge.target === nodeId).length,
    outbound: edges.filter((edge) => edge.source === nodeId).length,
  };
}

export function countNodeCtes(nodes: LineageNode[]): number {
  return nodes.reduce((total, node) => total + node.ctes.length, 0);
}
