import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { TabId } from "../../../app/store/editorStore";
import { runProjectValidation, saveFileContent, type ValidationRunResult } from "../../../api/projects";

const DEFAULT_VALIDATE_CATEGORIES = ["general", "sql", "descriptions"];

interface UseSqlSaveFlowOptions {
  currentProjectId: string | null;
  activeFilePath: string | null;
  activeSqlTabId: string | null;
  modelId: string | null;
  latestValidationRun: ValidationRunResult | null;
  lastValidationCategories: string[] | null;
  userRole: "user" | "admin" | "viewer";
  validationAutoRun: boolean;
  setDraft: (value: string) => void;
  setSqlTabDirty: (tabId: string, isDirty: boolean) => void;
  setLastSavedAt: (value: Date | null) => void;
  setActiveTab: (tab: TabId) => void;
  setLatestValidationRun: (value: ValidationRunResult | null) => void;
  addToast: (
    title: string,
    type?: "success" | "info" | "error",
    options?: {
      description?: string;
      autoCloseMs?: number | null;
      action?: { label: string; onClick: () => void };
    },
  ) => void;
}

export function useSqlSaveFlow({
  currentProjectId,
  activeFilePath,
  activeSqlTabId,
  modelId,
  latestValidationRun,
  lastValidationCategories,
  userRole,
  validationAutoRun,
  setDraft,
  setSqlTabDirty,
  setLastSavedAt,
  setActiveTab,
  setLatestValidationRun,
  addToast,
}: UseSqlSaveFlowOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) => saveFileContent(currentProjectId as string, activeFilePath as string, content),
    onSuccess: async (_, savedContent) => {
      if (currentProjectId && activeFilePath) {
        queryClient.setQueryData(["fileContent", currentProjectId, activeFilePath], savedContent);
      }
      setDraft(savedContent);
      if (activeSqlTabId) setSqlTabDirty(activeSqlTabId, false);
      const savedAt = new Date();
      setLastSavedAt(savedAt);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["fileContent", currentProjectId, activeFilePath] }),
        queryClient.invalidateQueries({ queryKey: ["autocomplete", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["lineage", currentProjectId, modelId] }),
        queryClient.invalidateQueries({ queryKey: ["projectParameters", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["workflowStatus", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["modelWorkflow", currentProjectId, modelId] }),
      ]);
      const validationTimestamp = latestValidationRun?.timestamp ? new Date(latestValidationRun.timestamp).getTime() : null;
      const showValidateHint = userRole !== "viewer" && (validationTimestamp === null || validationTimestamp < savedAt.getTime());
      if (showValidateHint && currentProjectId) {
        addToast("✓ Сохранено", "success", {
          description: "Рекомендуется запустить Validate перед Build",
          autoCloseMs: 6000,
          action: {
            label: "Запустить →",
            onClick: async () => {
              setActiveTab("validate");
              try {
                const result = await runProjectValidation(currentProjectId, {
                  model_id: modelId ?? undefined,
                  categories: lastValidationCategories ?? DEFAULT_VALIDATE_CATEGORIES,
                });
                setLatestValidationRun(result);
                addToast("Validation completed", result.summary.errors > 0 ? "error" : "success");
              } catch {
                addToast("Validation failed", "error");
              }
            },
          },
        });
      } else {
        addToast("✓ Сохранено", "success", { autoCloseMs: 2000 });
      }
      if (validationAutoRun && currentProjectId && modelId) {
        try {
          const result = await runProjectValidation(currentProjectId, { model_id: modelId });
          setLatestValidationRun(result);
          addToast(
            `Auto validation: ${result.summary.errors} errors, ${result.summary.warnings} warnings, ${result.summary.passed} passed`,
            result.summary.errors > 0 ? "error" : "success",
          );
        } catch {
          addToast("Auto validation failed", "error");
        }
      }
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to save file";
      addToast(message, "error");
    },
  });
}
