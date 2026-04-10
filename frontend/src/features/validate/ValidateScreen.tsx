import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  applyValidationQuickFix,
  fetchFileContent,
  fetchModelWorkflow,
  fetchProjectWorkflowStatus,
  fetchValidationHistory,
  getDryRunQuickFix,
  runProjectValidation,
  type ValidationRuleResult,
  type ValidationRunResult,
} from "../../api/projects";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import { useValidationStore } from "../../app/store/validationStore";
import QuickFixPreviewModal from "./QuickFixPreviewModal";
import { getRouteLabel, routeValidationError } from "./utils/fileRouter";

type RuleStatusFilter = "all" | "pass" | "warning" | "error";
type QuickFixType = "add_field" | "rename_folder";

type QuickFixPreviewPayload = {
  payload: {
    type: QuickFixType;
    model_id?: string;
    file_path?: string;
    field_name?: string;
    new_name?: string;
  };
  preview: {
    filePath: string;
    description: string;
    diff: string;
  };
  ruleKey: string;
};

const CATEGORY_OPTIONS = ["general", "sql", "descriptions", "adb", "oracle", "postgresql"];

function makeRuleKey(item: ValidationRuleResult, index: number): string {
  return `${item.rule_id}-${item.file_path ?? "none"}-${item.line ?? 0}-${index}`;
}

function formatRunTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function groupByCategory(items: ValidationRuleResult[]): Array<{ category: string; rules: ValidationRuleResult[] }> {
  const byCategory = new Map<string, ValidationRuleResult[]>();
  for (const item of items) {
    const category = item.rule_id.split(".")[0] ?? "other";
    const list = byCategory.get(category) ?? [];
    list.push(item);
    byCategory.set(category, list);
  }

  return Array.from(byCategory.entries())
    .map(([category, rules]) => ({
      category,
      rules,
    }))
    .sort((a, b) => a.category.localeCompare(b.category));
}

function resolveGroupStatus(items: ValidationRuleResult[]): ValidationRuleResult["status"] {
  if (items.some((item) => item.status === "error")) return "error";
  if (items.some((item) => item.status === "warning")) return "warning";
  return "pass";
}

function resolveQuickFixType(rule: ValidationRuleResult): QuickFixType | null {
  if (rule.rule_id === "descriptions.comment_present") {
    return "add_field";
  }
  if (rule.rule_id.includes("folder")) {
    return "rename_folder";
  }
  return null;
}

function SummaryBar({
  passed,
  warnings,
  errors,
  activeFilter,
  onFilterChange,
}: {
  passed: number;
  warnings: number;
  errors: number;
  activeFilter: RuleStatusFilter;
  onFilterChange: (next: RuleStatusFilter) => void;
}) {
  return (
    <section className="validate-summary">
      <button
        type="button"
        className={activeFilter === "pass" ? "validate-summary-item is-active is-pass" : "validate-summary-item is-pass"}
        onClick={() => onFilterChange("pass")}
      >
        Passed: {passed}
      </button>
      <button
        type="button"
        className={activeFilter === "warning" ? "validate-summary-item is-active is-warning" : "validate-summary-item is-warning"}
        onClick={() => onFilterChange("warning")}
      >
        Warn: {warnings}
      </button>
      <button
        type="button"
        className={activeFilter === "error" ? "validate-summary-item is-active is-error" : "validate-summary-item is-error"}
        onClick={() => onFilterChange("error")}
      >
        Errors: {errors}
      </button>
    </section>
  );
}

function RuleRow({
  item,
  ruleKey,
  quickFixState,
  onQuickFix,
}: {
  item: ValidationRuleResult;
  ruleKey: string;
  quickFixState: "idle" | "loading" | "applied";
  onQuickFix: (item: ValidationRuleResult, type: QuickFixType, key: string) => void;
}) {
  const openFile = useEditorStore((state) => state.openFile);
  const setNavigateTo = useEditorStore((state) => state.setNavigateTo);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const setInitialParam = useUiStore((state) => state.setInitialParam);
  const setInitialModelId = useUiStore((state) => state.setInitialModelId);

  const routeLabel = getRouteLabel(item.file_path, item.line);
  const quickFixType = resolveQuickFixType(item);
  const canQuickFix = item.status !== "pass" && quickFixType !== null;

  return (
    <li className={`validate-rule-row is-${item.status}`}>
      <div className="validate-rule-main">
        <span className={`validate-rule-dot is-${item.status}`} />
        <div>
          <p className="validate-rule-title">{item.name}</p>
          <p className="validate-rule-message">{item.message}</p>
          {item.file_path ? (
            <p className="validate-rule-path">
              {item.file_path}
              {item.line ? `:${item.line}` : ""}
            </p>
          ) : null}
        </div>
      </div>
      <div className="validate-rule-actions">
        <button
          type="button"
          className="action-btn"
          onClick={() => {
            const route = routeValidationError(item.file_path, item.line);
            switch (route.tab) {
              case "sql":
                openFile(route.filePath);
                setNavigateTo({ path: route.filePath, line: route.line ?? null });
                setActiveTab("sql");
                break;
              case "model":
                setInitialModelId(route.modelId || null);
                setActiveTab("model");
                break;
              case "parameters":
                if (route.paramId) {
                  setInitialParam({ id: route.paramId, scope: route.scope ?? "global" });
                }
                setActiveTab("parameters");
                break;
              case "lineage":
                setActiveTab("lineage");
                break;
            }
          }}
        >
          {routeLabel}
        </button>
        {canQuickFix ? (
          <button
            type="button"
            className="action-btn"
            disabled={quickFixState === "loading"}
            onClick={() => onQuickFix(item, quickFixType as QuickFixType, ruleKey)}
            title={quickFixType === "add_field" ? "Add missing description field to model.yml" : "Rename folder"}
          >
            {quickFixState === "loading" ? "⟳" : quickFixState === "applied" ? "✓ Применено" : "✦ Quick fix"}
          </button>
        ) : null}
      </div>
    </li>
  );
}

function CategoryGroup({
  category,
  items,
  defaultExpanded,
  quickFixPendingKey,
  appliedQuickFixKeys,
  onQuickFix,
}: {
  category: string;
  items: ValidationRuleResult[];
  defaultExpanded: boolean;
  quickFixPendingKey: string | null;
  appliedQuickFixKeys: Set<string>;
  onQuickFix: (item: ValidationRuleResult, type: QuickFixType, key: string) => void;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const status = resolveGroupStatus(items);
  const passed = items.filter((item) => item.status === "pass").length;
  const label = `${passed}/${items.length}`;
  return (
    <section className="validate-category">
      <button type="button" className="validate-category-head" onClick={() => setExpanded((prev) => !prev)}>
        <span className={`validate-category-indicator is-${status}`} />
        <strong>{category}</strong>
        <span className="validate-category-counter">{label}</span>
        <span className="validate-category-caret">{expanded ? "▾" : "▸"}</span>
      </button>
      {expanded ? (
        <ul className="validate-rule-list">
          {items.map((item, index) => {
            const key = makeRuleKey(item, index);
            const quickFixState = quickFixPendingKey === key ? "loading" : appliedQuickFixKeys.has(key) ? "applied" : "idle";
            return <RuleRow key={key} item={item} ruleKey={key} quickFixState={quickFixState} onQuickFix={onQuickFix} />;
          })}
        </ul>
      ) : null}
    </section>
  );
}

function buildFrontendQuickFixPreview(options: {
  filePath: string;
  content: string;
  type: QuickFixType;
}): { filePath: string; description: string; diff: string } {
  const lines = options.content.split("\n");
  if (options.type === "add_field") {
    const insertAfter = lines.findIndex((line) => line.includes("- name:"));
    if (insertAfter >= 0) {
      const contextLine = lines[insertAfter] ?? "";
      return {
        filePath: options.filePath,
        description: "добавить поле description",
        diff: `${contextLine}\n+     description: ""`,
      };
    }
    return {
      filePath: options.filePath,
      description: "добавить поле description",
      diff: '+ description: ""',
    };
  }

  return {
    filePath: options.filePath,
    description: "переименовать folder",
    diff: "~ folder name will be updated",
  };
}

export default function ValidateScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const addToast = useUiStore((state) => state.addToast);
  const dismissedHistoryWarning = useUiStore((state) => state.dismissedHistoryWarning);
  const setDismissedHistoryWarning = useUiStore((state) => state.setDismissedHistoryWarning);
  const latestRun = useValidationStore((state) => state.latestRun);
  const setLatestRun = useValidationStore((state) => state.setLatestRun);
  const setLastCategories = useValidationStore((state) => state.setLastCategories);
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<RuleStatusFilter>("all");
  const [selectedCategories, setSelectedCategories] = useState<string[]>(CATEGORY_OPTIONS);
  const [quickFixPendingKey, setQuickFixPendingKey] = useState<string | null>(null);
  const [appliedQuickFixKeys, setAppliedQuickFixKeys] = useState<Set<string>>(new Set());
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewData, setPreviewData] = useState<QuickFixPreviewPayload | null>(null);
  const [wsProgress, setWsProgress] = useState<number | null>(null);
  const [wsStage, setWsStage] = useState<string | null>(null);

  const historyQuery = useQuery({
    queryKey: ["validationHistory", currentProjectId],
    queryFn: () => fetchValidationHistory(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });
  const workflowStatusQuery = useQuery({
    queryKey: ["workflowStatus", currentProjectId],
    queryFn: () => fetchProjectWorkflowStatus(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const runMutation = useMutation({
    mutationFn: (modelId: string | null) =>
      runProjectValidation(currentProjectId as string, {
        model_id: modelId ?? undefined,
        categories: selectedCategories,
      }),
    onSuccess: async (run) => {
      setLatestRun(run);
      setLastCategories(selectedCategories);
      await queryClient.invalidateQueries({ queryKey: ["validationHistory", currentProjectId] });
      addToast("Validation completed", run.summary.errors > 0 ? "error" : "success");
    },
    onError: () => {
      addToast("Validation failed", "error");
    },
  });

  const runValidationViaWs = (modelId: string | null) => {
    if (!currentProjectId) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/validation/${currentProjectId}`);
    setWsProgress(0);
    setWsStage("connecting");
    setLastCategories(selectedCategories);

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          model_id: modelId ?? undefined,
          categories: selectedCategories,
        }),
      );
    };
    ws.onmessage = async (event) => {
      const payload = JSON.parse(event.data) as
        | { type: "progress"; percent: number; stage: string }
        | { type: "done"; result: ValidationRunResult }
        | { type: "error"; message: string };

      if (payload.type === "progress") {
        setWsProgress(payload.percent);
        setWsStage(payload.stage);
        return;
      }
      if (payload.type === "done") {
        setLatestRun(payload.result);
        setWsProgress(100);
        setWsStage("completed");
        await queryClient.invalidateQueries({ queryKey: ["validationHistory", currentProjectId] });
        addToast("Validation completed", payload.result.summary.errors > 0 ? "error" : "success");
        ws.close();
        return;
      }
      addToast(payload.message, "error");
      ws.close();
    };
    ws.onerror = () => {
      setWsProgress(null);
      setWsStage(null);
      runMutation.mutate(modelId);
    };
    ws.onclose = () => {
      setTimeout(() => {
        setWsProgress(null);
        setWsStage(null);
      }, 1000);
    };
  };

  const activeRun = useMemo(() => {
    const scopedLatestRun = latestRun?.project === currentProjectId ? latestRun : null;
    const historyLatest = historyQuery.data?.[0] ?? null;
    if (!historyLatest) return scopedLatestRun;
    if (!scopedLatestRun) return historyLatest;
    return new Date(scopedLatestRun.timestamp).getTime() >= new Date(historyLatest.timestamp).getTime()
      ? scopedLatestRun
      : historyLatest;
  }, [currentProjectId, historyQuery.data, latestRun]);

  const quickFixApplyMutation = useMutation({
    mutationFn: async (payload: QuickFixPreviewPayload) =>
      applyValidationQuickFix(currentProjectId as string, {
        ...payload.payload,
        rerun: true,
      }),
    onSuccess: async (result, payload) => {
      if (result.validation) {
        setLatestRun(result.validation);
      }
      addToast(`✓ Исправлено: ${payload.preview.description}`, "success");
      setAppliedQuickFixKeys((prev) => {
        const next = new Set(prev);
        next.add(payload.ruleKey);
        return next;
      });
      window.setTimeout(() => {
        setAppliedQuickFixKeys((prev) => {
          const next = new Set(prev);
          next.delete(payload.ruleKey);
          return next;
        });
      }, 3000);
      await queryClient.invalidateQueries({ queryKey: ["validationHistory", currentProjectId] });
    },
    onError: () => {
      addToast("Quick fix failed", "error");
    },
    onSettled: () => {
      setQuickFixPendingKey(null);
    },
  });

  const filteredRules = useMemo(() => {
    if (!activeRun) return [] as ValidationRuleResult[];
    if (statusFilter === "all") return activeRun.rules;
    return activeRun.rules.filter((item) => item.status === statusFilter);
  }, [activeRun, statusFilter]);

  const grouped = useMemo(() => groupByCategory(filteredRules), [filteredRules]);

  const historyItems = useMemo(() => {
    const items = historyQuery.data ?? [];
    return items.slice(0, 5);
  }, [historyQuery.data]);

  const activeRunWorkflowQuery = useQuery({
    queryKey: ["modelWorkflow", currentProjectId, activeRun?.model],
    queryFn: () => fetchModelWorkflow(currentProjectId as string, activeRun?.model as string),
    enabled: Boolean(currentProjectId && activeRun?.model),
  });
  const validationIsStale = useMemo(() => {
    const validationTimestamp = activeRun?.workflow_updated_at ?? null;
    const workflowTimestamp = activeRunWorkflowQuery.data?.updated_at ?? null;
    if (!validationTimestamp || !workflowTimestamp) return false;
    return new Date(workflowTimestamp).getTime() > new Date(validationTimestamp).getTime();
  }, [activeRun?.workflow_updated_at, activeRunWorkflowQuery.data?.updated_at]);

  if (!currentProjectId) {
    return (
      <section className="workbench">
        <h1>Validate Screen</h1>
        <p>Select project to run validation.</p>
      </section>
    );
  }

  const runModelId = activeRun?.model ?? null;

  return (
    <section className="workbench">
      <div className="validate-head">
        <h1>Validate Screen</h1>
        <div className="validate-actions">
          <button type="button" className="action-btn" onClick={() => setStatusFilter("all")}>
            All
          </button>
          <button type="button" className="action-btn" onClick={() => setStatusFilter("pass")}>
            Passed
          </button>
          <button type="button" className="action-btn" onClick={() => setStatusFilter("warning")}>
            Warn
          </button>
          <button type="button" className="action-btn" onClick={() => setStatusFilter("error")}>
            Errors
          </button>
          <button
            type="button"
            className="action-btn action-btn-primary"
            disabled={runMutation.isPending || selectedCategories.length === 0}
            onClick={() => runValidationViaWs(runModelId)}
          >
            {runMutation.isPending || wsProgress !== null ? "Running..." : "Re-run"}
          </button>
        </div>
      </div>
      {wsProgress !== null ? (
        <p className="validate-meta">
          Validation progress: {wsProgress}%{wsStage ? ` (${wsStage})` : ""}
        </p>
      ) : null}

      <div className="validate-category-filter">
        <span className="validate-category-filter-label">Categories:</span>
        <div className="validate-category-filter-options">
          {CATEGORY_OPTIONS.map((category) => (
            <label key={category} className="validate-category-filter-item">
              <input
                type="checkbox"
                checked={selectedCategories.includes(category)}
                onChange={(event) => {
                  const checked = event.target.checked;
                  setSelectedCategories((prev) => {
                    if (checked) {
                      return prev.includes(category) ? prev : [...prev, category];
                    }
                    return prev.filter((item) => item !== category);
                  });
                }}
              />
              {category}
            </label>
          ))}
        </div>
      </div>

      {!activeRun ? (
        <p>No validation runs yet.</p>
      ) : (
        <>
          <SummaryBar
            passed={activeRun.summary.passed}
            warnings={activeRun.summary.warnings}
            errors={activeRun.summary.errors}
            activeFilter={statusFilter}
            onFilterChange={setStatusFilter}
          />
          <p className="validate-meta">
            Last run: {formatRunTimestamp(activeRun.timestamp)} | Model: <code>{activeRun.model}</code>
          </p>
          <p className="validate-meta">
            Workflow state: {activeRunWorkflowQuery.data?.status ?? workflowStatusQuery.data?.overall ?? workflowStatusQuery.data?.status ?? "missing"} |
            Workflow updated: {activeRunWorkflowQuery.data?.updated_at ? formatRunTimestamp(activeRunWorkflowQuery.data.updated_at) : "—"}
            {validationIsStale ? " | Validation is stale" : ""}
          </p>
          <div className="validate-groups">
            {grouped.length === 0 ? (
              <p className="validate-empty">No rules for selected filter.</p>
            ) : (
              grouped.map((group) => (
                <CategoryGroup
                  key={group.category}
                  category={group.category}
                  items={group.rules}
                  defaultExpanded={group.rules.some((item) => item.status !== "pass")}
                  quickFixPendingKey={quickFixPendingKey}
                  appliedQuickFixKeys={appliedQuickFixKeys}
                  onQuickFix={async (item, type, key) => {
                    if (!currentProjectId) return;
                    setQuickFixPendingKey(key);
                    setPreviewLoading(true);
                    const payload = {
                      type,
                      model_id: activeRun?.model,
                      file_path: item.file_path ?? undefined,
                      field_name: type === "add_field" ? "description" : undefined,
                    };
                    try {
                      const dryRun = await getDryRunQuickFix(currentProjectId, {
                        ...payload,
                        model_id: payload.model_id ?? "",
                      });
                      setPreviewData({
                        payload,
                        ruleKey: key,
                        preview: {
                          filePath: dryRun.file_path,
                          description: dryRun.description,
                          diff: dryRun.diff,
                        },
                      });
                    } catch {
                      const fallbackPath = payload.file_path ?? `model/${payload.model_id}/model.yml`;
                      try {
                        const content = await fetchFileContent(currentProjectId, fallbackPath);
                        const preview = buildFrontendQuickFixPreview({
                          type,
                          filePath: fallbackPath,
                          content,
                        });
                        setPreviewData({ payload, ruleKey: key, preview });
                      } catch {
                        setPreviewData({
                          payload,
                          ruleKey: key,
                          preview: {
                            filePath: fallbackPath,
                            description: type === "add_field" ? "добавить поле description" : "переименовать folder",
                            diff: type === "add_field" ? "+ description: \"\"" : "~ folder name will be updated",
                          },
                        });
                      }
                    } finally {
                      setPreviewLoading(false);
                      setPreviewModalOpen(true);
                      setQuickFixPendingKey(null);
                    }
                  }}
                />
              ))
            )}
          </div>
        </>
      )}

      <section className="validate-history">
        <h2>Recent runs</h2>
        {!dismissedHistoryWarning ? (
          <div className="session-history-banner">
            <span>История сессии - сбрасывается при перезапуске сервера</span>
            <button type="button" onClick={() => setDismissedHistoryWarning(true)}>
              Понятно ✕
            </button>
          </div>
        ) : null}
        {historyItems.length === 0 ? (
          <p className="validate-empty">No history yet.</p>
        ) : (
          <ul className="validate-history-list">
            {historyItems.map((run: ValidationRunResult) => (
              <li key={run.run_id} className="validate-history-item">
                <button
                  type="button"
                  className="validate-history-open"
                  onClick={() => {
                    setLatestRun(run);
                    addToast(`Loaded run ${run.run_id}`, "info");
                  }}
                >
                  {formatRunTimestamp(run.timestamp)} | {run.model} | E:{run.summary.errors} W:{run.summary.warnings} P:{run.summary.passed}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <QuickFixPreviewModal
        isOpen={previewModalOpen}
        isLoading={quickFixApplyMutation.isPending || previewLoading}
        preview={previewData?.preview ?? null}
        onClose={() => {
          setPreviewModalOpen(false);
          setPreviewData(null);
          setQuickFixPendingKey(null);
        }}
        onConfirm={() => {
          if (!previewData) return;
          setPreviewModalOpen(false);
          quickFixApplyMutation.mutate(previewData);
        }}
      />
    </section>
  );
}
