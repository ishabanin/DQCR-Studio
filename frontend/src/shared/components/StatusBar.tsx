import { useEffect, useMemo, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { fetchProjectWorkflowStatus, rebuildModelWorkflow, type WorkflowStatus } from "../../api/projects";
import { useContextStore } from "../../app/store/contextStore";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";

const WORKFLOW_LABELS: Record<WorkflowStatus, string> = {
  ready: "✓ workflow",
  stale: "⚠ cache stale",
  building: "⟳ building…",
  error: "✗ cache error",
  missing: "⚪ no cache",
};

const WORKFLOW_COLORS: Record<WorkflowStatus, string> = {
  ready: "var(--color-text-success)",
  stale: "var(--color-text-warning)",
  building: "var(--color-text-secondary)",
  error: "var(--color-text-danger)",
  missing: "var(--color-text-tertiary)",
};

export default function StatusBar() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeContext = useContextStore((state) => state.activeContext);
  const activeContexts = useContextStore((state) => state.activeContexts);
  const multiMode = useContextStore((state) => state.multiMode);
  const activeFilePath = useEditorStore((state) => state.activeFilePath);
  const addToast = useUiStore((state) => state.addToast);
  const setCacheStatus = useUiStore((state) => state.setCacheStatus);
  const activeModelId = useMemo(() => {
    if (!activeFilePath) return null;
    const parts = activeFilePath.split("/").filter(Boolean);
    const modelIndex = parts.findIndex((part) => part === "model");
    if (modelIndex < 0 || modelIndex + 1 >= parts.length) return null;
    return parts[modelIndex + 1] ?? null;
  }, [activeFilePath]);

  const workflowStatusQuery = useQuery({
    queryKey: ["workflowStatus", currentProjectId],
    queryFn: () => fetchProjectWorkflowStatus(currentProjectId as string),
    enabled: Boolean(currentProjectId),
    refetchInterval: currentProjectId ? 10000 : false,
  });
  const rebuildTriggeredRef = useRef(false);
  const rebuildMutation = useMutation({
    mutationFn: async () => {
      if (!currentProjectId) return;
      const models = workflowStatusQuery.data?.models ?? [];
      const targetModels = activeModelId
        ? models.filter((item) => item.model_id === activeModelId && (item.status === "stale" || item.status === "error"))
        : models.filter((item) => item.status === "stale" || item.status === "error");
      const modelIds = targetModels.map((item) => item.model_id);
      await Promise.all(modelIds.map((modelId) => rebuildModelWorkflow(currentProjectId, modelId)));
    },
    onError: () => {
      addToast("Workflow rebuild failed", "error");
    },
  });
  const activeModelState = useMemo(() => {
    const models = workflowStatusQuery.data?.models ?? [];
    if (activeModelId) {
      const selected = models.find((item) => item.model_id === activeModelId);
      if (selected) return selected;
    }
    return models[0] ?? null;
  }, [activeModelId, workflowStatusQuery.data?.models]);
  const overallStatus = (workflowStatusQuery.data?.overall ?? workflowStatusQuery.data?.status ?? "missing") as WorkflowStatus;
  const statusToShow = rebuildMutation.isPending ? "building" : overallStatus;
  const isRebuildDisabled = rebuildMutation.isPending || statusToShow === "building";

  useEffect(() => {
    setCacheStatus(statusToShow);
  }, [setCacheStatus, statusToShow]);

  useEffect(() => {
    if (!rebuildTriggeredRef.current) return;
    if (statusToShow !== "ready") return;
    addToast("✓ Workflow cache обновлён", "success");
    rebuildTriggeredRef.current = false;
  }, [addToast, statusToShow]);

  const handleRebuild = () => {
    if (!currentProjectId || isRebuildDisabled) return;
    rebuildTriggeredRef.current = true;
    rebuildMutation.mutate();
  };

  return (
    <footer className="statusbar">
      <span>Project: {currentProjectId ?? "none"}</span>
      <span>Context: {multiMode ? activeContexts.join(", ") : activeContext}</span>
      <button
        type="button"
        className="statusbar-workflow-btn"
        onClick={handleRebuild}
        disabled={isRebuildDisabled}
        style={{ color: WORKFLOW_COLORS[statusToShow] }}
      >
        {WORKFLOW_LABELS[statusToShow]}
      </button>
      <span>Model source: {activeModelState?.source ?? "—"}</span>
      <span>
        Workflow at: {activeModelState?.updated_at ? new Date(activeModelState.updated_at).toLocaleString() : "—"}
      </span>
    </footer>
  );
}
