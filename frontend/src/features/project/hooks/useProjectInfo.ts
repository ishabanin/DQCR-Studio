import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  type ContextItem,
  type FileNode,
  type ProjectParameterItem,
  type WorkflowProjectStatus,
  fetchFileContent,
  fetchProjectContexts,
  fetchProjectParameters,
  fetchProjectTree,
  fetchProjectWorkflowStatus,
} from "../../../api/projects";

export type ModelCacheStatus = "ready" | "stale" | "building" | "error" | "missing";

export interface ModelSummary {
  id: string;
  folderCount: number;
  sqlCount: number;
  paramCount: number;
  targetTable: string | null;
  cacheStatus: ModelCacheStatus;
  template: string | null;
}

export interface ProjectInfoData {
  models: ModelSummary[];
  totalFolders: number;
  totalSqlFiles: number;
  totalContexts: number;
  totalGlobalParams: number;
  totalModelParams: number;
  contexts: ContextItem[];
  parameters: ProjectParameterItem[];
  globalParams: ProjectParameterItem[];
  projectYml: string;
}

function countTreeStats(root: FileNode | null): { totalFolders: number; totalSqlFiles: number } {
  if (!root) return { totalFolders: 0, totalSqlFiles: 0 };

  let totalFolders = 0;
  let totalSqlFiles = 0;
  const stack: FileNode[] = [root];

  while (stack.length > 0) {
    const node = stack.pop();
    if (!node) continue;

    if (node.type === "directory" && node.path !== ".") {
      totalFolders += 1;
    }
    if (node.type === "file" && node.name.toLowerCase().endsWith(".sql")) {
      totalSqlFiles += 1;
    }

    for (const child of node.children ?? []) {
      stack.push(child);
    }
  }

  return { totalFolders, totalSqlFiles };
}

function countSqlFiles(node: FileNode | undefined): number {
  if (!node) return 0;
  let count = 0;
  const stack: FileNode[] = [node];
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) continue;
    if (current.type === "file" && current.name.toLowerCase().endsWith(".sql")) {
      count += 1;
    }
    for (const child of current.children ?? []) {
      stack.push(child);
    }
  }
  return count;
}

function aggregateModels(tree: FileNode | null, workflowStatus: WorkflowProjectStatus | undefined): ModelSummary[] {
  if (!tree) return [];

  const modelRoot = tree.children?.find((node) => node.type === "directory" && node.name.toLowerCase() === "model");
  const workflowMap = new Map(
    (workflowStatus?.models ?? []).map((item) => [
      item.model_id,
      item.status,
    ]),
  );

  return (modelRoot?.children ?? [])
    .filter((node): node is FileNode => node.type === "directory")
    .map((modelNode) => {
      const workflowNode =
        modelNode.children?.find((child) => child.type === "directory" && ["workflow", "sql"].includes(child.name.toLowerCase())) ??
        null;
      const parameterNode = modelNode.children?.find((child) => child.type === "directory" && child.name.toLowerCase() === "parameters") ?? null;
      const folders = (workflowNode?.children ?? []).filter((child) => child.type === "directory");
      const paramFiles = (parameterNode?.children ?? []).filter(
        (child) => child.type === "file" && [".yml", ".yaml"].some((ext) => child.name.toLowerCase().endsWith(ext)),
      );

      return {
        id: modelNode.name,
        folderCount: folders.length,
        sqlCount: countSqlFiles(workflowNode ?? undefined),
        paramCount: paramFiles.length,
        targetTable: null,
        cacheStatus: workflowMap.get(modelNode.name) ?? "missing",
        template: null,
      };
    })
    .sort((left, right) => left.id.localeCompare(right.id));
}

export function useProjectInfo(projectId: string | null) {
  const treeQuery = useQuery({
    queryKey: ["project-info", "tree", projectId],
    queryFn: () => fetchProjectTree(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const workflowQuery = useQuery({
    queryKey: ["project-info", "workflow", projectId],
    queryFn: () => fetchProjectWorkflowStatus(projectId as string),
    enabled: Boolean(projectId),
    refetchInterval: projectId ? 10_000 : false,
  });

  const contextsQuery = useQuery({
    queryKey: ["project-info", "contexts", projectId],
    queryFn: () => fetchProjectContexts(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });

  const parametersQuery = useQuery({
    queryKey: ["project-info", "parameters", projectId],
    queryFn: () => fetchProjectParameters(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const projectYmlQuery = useQuery({
    queryKey: ["project-info", "project-yml", projectId],
    queryFn: () => fetchFileContent(projectId as string, "project.yml"),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const data = useMemo<ProjectInfoData | null>(() => {
    if (!treeQuery.data) return null;

    const parameters = parametersQuery.data ?? [];
    const globalParams = parameters.filter((item) => item.scope === "global");
    const modelParams = parameters.filter((item) => item.scope.startsWith("model:"));
    const totals = countTreeStats(treeQuery.data);

    return {
      models: aggregateModels(treeQuery.data, workflowQuery.data),
      totalFolders: totals.totalFolders,
      totalSqlFiles: totals.totalSqlFiles,
      totalContexts: (contextsQuery.data ?? []).length,
      totalGlobalParams: globalParams.length,
      totalModelParams: modelParams.length,
      contexts: contextsQuery.data ?? [],
      parameters,
      globalParams,
      projectYml: projectYmlQuery.data ?? "",
    };
  }, [contextsQuery.data, parametersQuery.data, projectYmlQuery.data, treeQuery.data, workflowQuery.data]);

  return {
    data,
    isLoading:
      treeQuery.isLoading ||
      contextsQuery.isLoading ||
      parametersQuery.isLoading ||
      projectYmlQuery.isLoading,
    isFetching:
      treeQuery.isFetching ||
      workflowQuery.isFetching ||
      contextsQuery.isFetching ||
      parametersQuery.isFetching ||
      projectYmlQuery.isFetching,
    error:
      treeQuery.error ??
      workflowQuery.error ??
      contextsQuery.error ??
      parametersQuery.error ??
      projectYmlQuery.error ??
      null,
    refetch: () =>
      Promise.all([
        treeQuery.refetch(),
        workflowQuery.refetch(),
        contextsQuery.refetch(),
        parametersQuery.refetch(),
        projectYmlQuery.refetch(),
      ]),
  };
}
