import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchProjectWorkflowStatus } from "../../api/projects";
import { useContextStore } from "../../app/store/contextStore";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";

export default function StatusBar() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeContext = useContextStore((state) => state.activeContext);
  const activeContexts = useContextStore((state) => state.activeContexts);
  const multiMode = useContextStore((state) => state.multiMode);
  const activeFilePath = useEditorStore((state) => state.activeFilePath);
  const workflowStatusQuery = useQuery({
    queryKey: ["workflowStatus", currentProjectId],
    queryFn: () => fetchProjectWorkflowStatus(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const activeModelId = useMemo(() => {
    if (!activeFilePath) return null;
    const parts = activeFilePath.split("/").filter(Boolean);
    const modelIndex = parts.findIndex((part) => part === "model");
    if (modelIndex < 0 || modelIndex + 1 >= parts.length) return null;
    return parts[modelIndex + 1] ?? null;
  }, [activeFilePath]);
  const activeModelState = useMemo(() => {
    const models = workflowStatusQuery.data?.models ?? [];
    if (activeModelId) {
      const selected = models.find((item) => item.model_id === activeModelId);
      if (selected) return selected;
    }
    return models[0] ?? null;
  }, [activeModelId, workflowStatusQuery.data?.models]);

  return (
    <footer className="statusbar">
      <span>Project: {currentProjectId ?? "none"}</span>
      <span>Context: {multiMode ? activeContexts.join(", ") : activeContext}</span>
      <span>Workflow: {workflowStatusQuery.data?.status ?? "missing"}</span>
      <span>Model source: {activeModelState?.source ?? "—"}</span>
      <span>
        Workflow at: {activeModelState?.updated_at ? new Date(activeModelState.updated_at).toLocaleString() : "—"}
      </span>
    </footer>
  );
}
