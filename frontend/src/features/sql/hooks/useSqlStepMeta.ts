import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchModelWorkflow } from "../../../api/projects";
import { useContextStore } from "../../../app/store/contextStore";

interface SqlStepMetaResult {
  workflow: Record<string, unknown> | null;
  step: Record<string, unknown> | null;
  status: "ok" | "no-cache" | "not-found";
  workflowStatus: string;
  isLoading: boolean;
}

function parseSqlKeyFromPath(filePath: string | null): { folder: string; queryName: string } | null {
  if (!filePath) return null;
  const parts = filePath.split("/").filter(Boolean);
  const workflowIndex = parts.findIndex((part) => part === "workflow");
  if (workflowIndex < 0) return null;
  const folder = parts[workflowIndex + 1];
  const fileName = parts[workflowIndex + 2];
  if (!folder || !fileName || !fileName.endsWith(".sql")) return null;
  return { folder, queryName: fileName.replace(/\.sql$/i, "") };
}

function getMatchingStep(
  workflow: Record<string, unknown>,
  key: { folder: string; queryName: string },
  activeContext: string,
): Record<string, unknown> | null {
  const stepsRaw = workflow.steps;
  if (!Array.isArray(stepsRaw)) return null;

  const expectedPrefix = `${key.folder}/${key.queryName}`;

  const sqlSteps = stepsRaw
    .filter((step): step is Record<string, unknown> => typeof step === "object" && step !== null)
    .filter((step) => step.step_type === "sql")
    .filter((step) => {
      const fullName = typeof step.full_name === "string" ? step.full_name : "";
      return !fullName.includes("/cte/");
    })
    .filter((step) => {
      const fullName = typeof step.full_name === "string" ? step.full_name : "";
      return fullName === expectedPrefix || fullName.startsWith(`${expectedPrefix}/`);
    });

  if (sqlSteps.length === 0) return null;

  const exactContext = sqlSteps.find((step) => step.context === activeContext);
  if (exactContext) return exactContext;

  const allContext = sqlSteps.find((step) => step.context === "all");
  if (allContext) return allContext;

  return sqlSteps[0] ?? null;
}

export function useSqlStepMeta(projectId: string | null, modelId: string | null, filePath: string | null): SqlStepMetaResult {
  const activeContext = useContextStore((state) => state.activeContext);

  const workflowQuery = useQuery({
    queryKey: ["modelWorkflow", projectId, modelId],
    queryFn: () => fetchModelWorkflow(projectId as string, modelId as string),
    enabled: Boolean(projectId && modelId),
  });

  return useMemo(() => {
    const workflowStatus = workflowQuery.data?.status ?? "missing";
    const workflowRaw = workflowQuery.data?.workflow;
    const workflow = workflowRaw && typeof workflowRaw === "object" ? (workflowRaw as Record<string, unknown>) : null;

    if (!workflow || workflowStatus !== "ready") {
      return {
        workflow,
        step: null,
        status: "no-cache" as const,
        workflowStatus,
        isLoading: workflowQuery.isLoading,
      };
    }

    const sqlKey = parseSqlKeyFromPath(filePath);
    if (!sqlKey) {
      return {
        workflow,
        step: null,
        status: "not-found" as const,
        workflowStatus,
        isLoading: workflowQuery.isLoading,
      };
    }

    const step = getMatchingStep(workflow, sqlKey, activeContext);
    if (!step) {
      return {
        workflow,
        step: null,
        status: "not-found" as const,
        workflowStatus,
        isLoading: workflowQuery.isLoading,
      };
    }

    return {
      workflow,
      step,
      status: "ok" as const,
      workflowStatus,
      isLoading: workflowQuery.isLoading,
    };
  }, [activeContext, filePath, workflowQuery.data?.status, workflowQuery.data?.workflow, workflowQuery.isLoading]);
}
