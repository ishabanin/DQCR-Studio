import { FileNode } from "../../api/projects";

export function groupRootChildren(root: FileNode): FileNode[] {
  return root.children ?? [];
}

export function isLikelyGroupFolder(name: string): boolean {
  const normalized = name.toLowerCase();
  return ["model", "models", "contexts", "parameters", "templates"].includes(normalized);
}

