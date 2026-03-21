import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import YAML from "yaml";

import {
  type FileNode,
  type ProjectParameterItem,
  type WorkflowProjectStatus,
  fetchFileContent,
  fetchProjectContexts,
  fetchProjectParameters,
  fetchProjectTree,
  fetchProjectWorkflowStatus,
} from "../../../api/projects";
import type {
  ContextInfo,
  ModelCacheStatus,
  ModelSummary,
  ParamInfo,
  ProjectInfoData,
  ProjectSettings,
  PropertyEntry,
} from "../types";

const SYSTEM_PROP_KEYS = ["version", "owner", "dqcr_visibility", "dqcr_tags"];

function countSqlFiles(node: FileNode | null | undefined): number {
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

function parseSettingsAndProperties(ymlContent: string): { settings: ProjectSettings; properties: PropertyEntry[] } {
  let parsed: Record<string, unknown> = {};

  try {
    const value = YAML.parse(ymlContent) as Record<string, unknown> | null;
    parsed = value ?? {};
  } catch {
    parsed = {};
  }

  const rawProperties =
    typeof parsed.properties === "object" && parsed.properties !== null
      ? (parsed.properties as Record<string, unknown>)
      : {};

  const settings: ProjectSettings = {
    name: typeof parsed.name === "string" ? parsed.name : "",
    description: typeof parsed.description === "string" ? parsed.description : "",
    template: typeof parsed.template === "string" ? parsed.template : "",
    version: typeof rawProperties.version === "string" ? rawProperties.version : "",
    owner: typeof rawProperties.owner === "string" ? rawProperties.owner : "",
  };

  const properties: PropertyEntry[] = Object.entries(rawProperties)
    .filter(([key]) => !SYSTEM_PROP_KEYS.includes(key))
    .map(([key, value], index) => ({
      id: `prop-${index}-${key}`,
      key,
      value: String(value ?? ""),
    }));

  return { settings, properties };
}

function aggregateModels(tree: FileNode | null, template: string, workflowStatus: WorkflowProjectStatus | undefined): {
  models: ModelSummary[];
  totalFolders: number;
  totalSqlFiles: number;
  cacheStatuses: Record<string, ModelCacheStatus>;
} {
  if (!tree) {
    return {
      models: [],
      totalFolders: 0,
      totalSqlFiles: 0,
      cacheStatuses: {},
    };
  }

  const modelRoot = tree.children?.find(
    (node) => node.type === "directory" && ["model", "models"].includes(node.name.toLowerCase()),
  );

  const cacheStatuses: Record<string, ModelCacheStatus> = {};
  for (const item of workflowStatus?.models ?? []) {
    cacheStatuses[item.model_id] = item.status;
  }

  const models: ModelSummary[] = [];
  let totalFolders = 0;
  let totalSqlFiles = 0;

  for (const modelNode of modelRoot?.children ?? []) {
    if (modelNode.type !== "directory") continue;

    const workflowNode = modelNode.children?.find(
      (child) => child.type === "directory" && ["workflow", "sql"].includes(child.name.toLowerCase()),
    );
    const parameterNode = modelNode.children?.find(
      (child) => child.type === "directory" && child.name.toLowerCase() === "parameters",
    );

    const workflowFolders = (workflowNode?.children ?? []).filter((child) => child.type === "directory");
    const sqlCount = countSqlFiles(workflowNode);
    const paramCount = (parameterNode?.children ?? []).filter(
      (child) => child.type === "file" && [".yml", ".yaml"].some((ext) => child.name.toLowerCase().endsWith(ext)),
    ).length;

    totalFolders += workflowFolders.length;
    totalSqlFiles += sqlCount;

    models.push({
      id: modelNode.name,
      folderCount: workflowFolders.length,
      sqlCount,
      paramCount,
      targetTable: null,
      template: template || null,
    });
  }

  models.sort((a, b) => a.id.localeCompare(b.id));

  return {
    models,
    totalFolders,
    totalSqlFiles,
    cacheStatuses,
  };
}

function toParamInfo(item: ProjectParameterItem): ParamInfo {
  return {
    id: `${item.scope}:${item.name}`,
    name: item.name,
    scope: item.scope,
    domain_type: item.domain_type,
    values: item.values,
  };
}

async function loadContexts(projectId: string, names: string[]): Promise<ContextInfo[]> {
  const results = await Promise.allSettled(
    names.map(async (name) => {
      const content = await fetchFileContent(projectId, `contexts/${name}.yml`);
      const parsed = (YAML.parse(content) as Record<string, unknown> | null) ?? {};

      const tools = Array.isArray(parsed.tools)
        ? parsed.tools.filter((item): item is string => typeof item === "string")
        : [];

      const constants =
        typeof parsed.constants === "object" && parsed.constants !== null
          ? (parsed.constants as Record<string, string | number | boolean>)
          : {};

      const flagsRaw =
        typeof parsed.flags === "object" && parsed.flags !== null
          ? (parsed.flags as Record<string, unknown>)
          : {};
      const flags = Object.fromEntries(
        Object.entries(flagsRaw).map(([key, value]) => [key, Boolean(value)]),
      );

      return {
        name,
        tools,
        constants,
        flags,
      };
    }),
  );

  return results
    .filter((result): result is PromiseFulfilledResult<ContextInfo> => result.status === "fulfilled")
    .map((result) => result.value);
}

export function useProjectInfo(projectId: string | null) {
  const treeQuery = useQuery({
    queryKey: ["project-info", "tree", projectId],
    queryFn: () => fetchProjectTree(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const projectYmlQuery = useQuery({
    queryKey: ["project-info", "project-yml", projectId],
    queryFn: () => fetchFileContent(projectId as string, "project.yml"),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const workflowQuery = useQuery({
    queryKey: ["project-info", "workflow", projectId],
    queryFn: () => fetchProjectWorkflowStatus(projectId as string),
    enabled: Boolean(projectId),
    refetchInterval: projectId ? 10_000 : false,
  });

  const contextNamesQuery = useQuery({
    queryKey: ["project-info", "contexts", projectId],
    queryFn: () => fetchProjectContexts(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });

  const contextsQuery = useQuery({
    queryKey: ["project-info", "contexts-content", projectId, contextNamesQuery.data?.map((item) => item.name).join(",")],
    queryFn: () => loadContexts(projectId as string, (contextNamesQuery.data ?? []).map((item) => item.name)),
    enabled: Boolean(projectId && contextNamesQuery.data),
    staleTime: 60_000,
  });

  const paramsQuery = useQuery({
    queryKey: ["project-info", "parameters", projectId],
    queryFn: () => fetchProjectParameters(projectId as string),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const data = useMemo<ProjectInfoData | null>(() => {
    if (!treeQuery.data || !projectYmlQuery.data) {
      return null;
    }

    const { settings, properties } = parseSettingsAndProperties(projectYmlQuery.data);
    const modelData = aggregateModels(treeQuery.data, settings.template, workflowQuery.data);
    const params = (paramsQuery.data ?? []).map(toParamInfo);
    const globalParams = params.filter((item) => item.scope === "global");

    return {
      settings,
      properties,
      models: modelData.models,
      cacheStatuses: modelData.cacheStatuses,
      totalFolders: modelData.totalFolders,
      totalSqlFiles: modelData.totalSqlFiles,
      totalContexts: (contextsQuery.data ?? []).length,
      contexts: contextsQuery.data ?? [],
      globalParams,
      modelScopedCount: params.filter((item) => item.scope !== "global").length,
      projectYml: projectYmlQuery.data,
    };
  }, [contextsQuery.data, paramsQuery.data, projectYmlQuery.data, treeQuery.data, workflowQuery.data]);

  return {
    data,
    isLoading: treeQuery.isLoading || projectYmlQuery.isLoading,
    isError:
      treeQuery.isError ||
      projectYmlQuery.isError ||
      workflowQuery.isError ||
      contextNamesQuery.isError ||
      contextsQuery.isError ||
      paramsQuery.isError,
    error:
      treeQuery.error ??
      projectYmlQuery.error ??
      workflowQuery.error ??
      contextNamesQuery.error ??
      contextsQuery.error ??
      paramsQuery.error ??
      null,
    refetch: () =>
      Promise.all([
        treeQuery.refetch(),
        projectYmlQuery.refetch(),
        workflowQuery.refetch(),
        contextNamesQuery.refetch(),
        contextsQuery.refetch(),
        paramsQuery.refetch(),
      ]),
  };
}
