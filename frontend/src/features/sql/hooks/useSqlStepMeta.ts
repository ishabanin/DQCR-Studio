import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchModelWorkflow } from "../../../api/projects";
import { useContextStore } from "../../../app/store/contextStore";
import { getStepMatchScore, parseSqlFileKey } from "../sqlStepUtils";

interface SqlStepMetaResult {
  workflow: Record<string, unknown> | null;
  step: Record<string, unknown> | null;
  status: "ok" | "no-cache" | "not-found";
  workflowStatus: string;
  isLoading: boolean;
}

function getMatchingStep(workflow: Record<string, unknown>, key: { folder: string; queryName: string }, activeContext: string): Record<string, unknown> | null {
  const stepsRaw = workflow.steps;
  if (!Array.isArray(stepsRaw)) return null;

  const sqlSteps = stepsRaw
    .filter((step): step is Record<string, unknown> => typeof step === "object" && step !== null)
    .map((step) => ({ step, score: getStepMatchScore(step, key, activeContext) }))
    .filter((item) => item.score >= 0)
    .sort((a, b) => b.score - a.score);

  return sqlSteps[0]?.step ?? null;
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

    const sqlKey = parseSqlFileKey(filePath);
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
