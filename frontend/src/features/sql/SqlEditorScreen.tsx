import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";

import {
  fetchBuildPreview,
  fetchFileContent,
  fetchModelConfigChain,
  fetchProjectAutocomplete,
  fetchProjectTree,
  runProjectValidation,
  saveFileContent,
} from "../../api/projects";
import { useTheme } from "../../app/providers/ThemeProvider";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import { useValidationStore } from "../../app/store/validationStore";
import { configureDqcrMonaco, DQCR_LANGUAGE_ID, getDqcrTheme, setDqcrAutocompleteData } from "./dqcrLanguage";

function Breadcrumb({ path }: { path: string }) {
  const parts = path.split("/").filter(Boolean);

  return (
    <div className="breadcrumb">
      {parts.map((part, index) => (
        <button key={`${part}-${index}`} type="button" className="crumb">
          {part}
        </button>
      ))}
    </div>
  );
}

function FileTabs() {
  const openFiles = useEditorStore((state) => state.openFiles);
  const activeFilePath = useEditorStore((state) => state.activeFilePath);
  const setActiveFile = useEditorStore((state) => state.setActiveFile);
  const closeFile = useEditorStore((state) => state.closeFile);
  const reorderFiles = useEditorStore((state) => state.reorderFiles);
  const dirtyFiles = useEditorStore((state) => state.dirtyFiles);

  return (
    <div className="file-tabs">
      {openFiles.map((filePath) => {
        const fileName = filePath.split("/").pop() ?? filePath;
        const isActive = activeFilePath === filePath;
        const isDirty = Boolean(dirtyFiles[filePath]);
        return (
          <div key={filePath} className={isActive ? "file-tab file-tab-active" : "file-tab"}>
            <button
              type="button"
              draggable
              onDragStart={(event) => {
                event.dataTransfer.setData("text/plain", filePath);
              }}
              onDragOver={(event) => {
                event.preventDefault();
              }}
              onDrop={(event) => {
                event.preventDefault();
                const fromPath = event.dataTransfer.getData("text/plain");
                if (!fromPath) return;
                reorderFiles(fromPath, filePath);
              }}
              onClick={() => setActiveFile(filePath)}
              className="file-tab-name"
            >
              {fileName}
              {isDirty ? " ●" : ""}
            </button>
            <button type="button" onClick={() => closeFile(filePath)} className="file-tab-close">
              x
            </button>
          </div>
        );
      })}
    </div>
  );
}

function parseSqlParameters(sql: string): string[] {
  const pattern = /\{\{\s*([^}]+?)\s*\}\}/g;
  const items = new Set<string>();
  for (const match of sql.matchAll(pattern)) {
    const expr = (match[1] ?? "").trim();
    if (!expr) continue;
    if (expr.includes("(")) continue;
    const token = expr.split(/\s|\|/)[0]?.trim();
    if (!token) continue;
    if (!/^[A-Za-z_][\w.]*$/.test(token)) continue;
    items.add(token);
  }
  return Array.from(items).sort((a, b) => a.localeCompare(b));
}

function parseSqlCtes(sql: string): string[] {
  const items = new Set<string>();
  for (const match of sql.matchAll(/\bwith\s+([A-Za-z_][\w]*)\s+as\s*\(/gi)) {
    items.add(match[1]);
  }
  for (const match of sql.matchAll(/,\s*([A-Za-z_][\w]*)\s+as\s*\(/gi)) {
    items.add(match[1]);
  }
  return Array.from(items);
}

function formatSqlBasic(raw: string): string {
  const source = raw.replace(/\r\n/g, "\n").trim();
  if (!source) return "";
  let sql = source.replace(/[ \t]+/g, " ");
  const breakKeywords = [
    "from",
    "where",
    "group by",
    "order by",
    "having",
    "left join",
    "right join",
    "inner join",
    "outer join",
    "join",
    "union all",
    "union",
    "limit",
    "offset",
  ];
  for (const keyword of breakKeywords) {
    const pattern = new RegExp(`\\b${keyword}\\b`, "gi");
    sql = sql.replace(pattern, `\n${keyword.toUpperCase()}`);
  }
  sql = sql
    .replace(/\bselect\b/gi, "SELECT")
    .replace(/\bwith\b/gi, "WITH")
    .replace(/\bas\b/gi, "AS")
    .replace(/\band\b/gi, "AND")
    .replace(/\bor\b/gi, "OR");

  return sql
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n");
}

function extractModelIdFromPath(path: string | null): string | null {
  if (!path) return null;
  const parts = path.split("/").filter(Boolean);
  const modelIndex = parts.findIndex((part) => part === "model");
  if (modelIndex < 0 || modelIndex + 1 >= parts.length) return null;
  return parts[modelIndex + 1] ?? null;
}

function resolveEditorLanguage(path: string | null): string {
  if (!path) return DQCR_LANGUAGE_ID;
  if (path.endsWith(".yml") || path.endsWith(".yaml")) return "yaml";
  if (path.endsWith(".sql")) return DQCR_LANGUAGE_ID;
  return "plaintext";
}

const DEFAULT_VALIDATE_CATEGORIES = ["general", "sql", "descriptions"];

function PriorityChainPanel({
  levels,
  resolved,
  parameterUsages,
  ctes,
  cteDefault,
  cteByContext,
  inlineCteConfigs,
  generatedOutputs,
  previewLoading,
  previewEngine,
  previewContent,
  onPreview,
  dataSource,
  fallback,
}: {
  levels: Array<{
    id: string;
    label: string;
    source_path: string | null;
    values: Record<string, string | null>;
  }>;
  resolved: Array<{
    key: string;
    value: string | null;
    source_level: string;
  }>;
  parameterUsages: Array<{
    name: string;
    domain_type: string | null;
    value_type: string | null;
  }>;
  ctes: string[];
  cteDefault: string | null;
  cteByContext: Record<string, string>;
  inlineCteConfigs: Record<string, string>;
  generatedOutputs: string[];
  previewLoading: boolean;
  previewEngine: string | null;
  previewContent: string;
  onPreview: (engine: string) => void;
  dataSource?: string;
  fallback?: boolean;
}) {
  const orderedLevels = ["template", "project", "model", "folder", "sql"];
  const levelById = new Map(levels.map((level) => [level.id, level]));

  return (
    <aside className="config-chain-panel">
      <h2>@config Priority Chain</h2>
      {fallback ? <p className="config-chain-placeholder">Fallback mode: workflow cache unavailable, values are file-derived.</p> : null}
      {dataSource && !fallback ? <p className="inspector-meta">source: {dataSource}</p> : null}
      {resolved.map((item) => (
        <div key={item.key} className="config-row">
          <div className="config-row-head">
            <code>{item.key}</code>
            <span className="config-resolved">
              resolved: <strong>{item.value ?? "—"}</strong>
            </span>
          </div>
          <div className="config-levels">
            {orderedLevels.map((levelId) => {
              const level = levelById.get(levelId);
              const rawValue = level?.values[item.key] ?? null;
              const isActive = item.source_level === levelId && rawValue !== null;
              return (
                <div
                  key={`${item.key}-${levelId}`}
                  className={isActive ? "config-level config-level-active" : "config-level"}
                  title={level?.source_path ?? ""}
                >
                  <span>{level?.label ?? levelId}</span>
                  <code>{rawValue ?? "—"}</code>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <section className="inspector-section">
        <h3>Parameters Used</h3>
        {parameterUsages.length === 0 ? (
          <p className="inspector-placeholder">No template parameters in current SQL.</p>
        ) : (
          <ul className="inspector-list">
            {parameterUsages.map((item) => (
              <li key={item.name}>
                <code>{item.name}</code>
                <span>{item.domain_type ?? "—"}</span>
                <span>{item.value_type ?? "—"}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="inspector-section">
        <h3>CTE Inspector</h3>
        <p className="inspector-meta">
          default: <strong>{cteDefault ?? "—"}</strong>
        </p>
        <p className="inspector-meta">
          by_context:{" "}
          {Object.keys(cteByContext).length > 0
            ? Object.entries(cteByContext)
                .map(([ctx, value]) => `${ctx}=${value}`)
                .join(", ")
            : "—"}
        </p>
        <p className="inspector-meta">
          ctes: {ctes.length > 0 ? ctes.join(", ") : "—"}
        </p>
        <p className="inspector-meta">
          inline_cte_configs:{" "}
          {Object.keys(inlineCteConfigs).length > 0
            ? Object.entries(inlineCteConfigs)
                .map(([key, value]) => `${key}=${value}`)
                .join(", ")
            : "—"}
        </p>
      </section>

      <section className="inspector-section">
        <h3>Generated Output</h3>
        <div className="generated-output-list">
          {generatedOutputs.map((engine) => (
            <button key={engine} type="button" className="generated-output-btn" onClick={() => onPreview(engine)}>
              Preview {engine}
            </button>
          ))}
        </div>
        {previewLoading ? <p className="inspector-placeholder">Generating preview...</p> : null}
        {previewEngine ? <p className="inspector-meta">engine: {previewEngine}</p> : null}
        {previewContent ? <pre className="generated-preview">{previewContent}</pre> : null}
      </section>
    </aside>
  );
}

export default function SqlEditorScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeTab = useEditorStore((state) => state.activeTab);
  const activeFilePath = useEditorStore((state) => state.activeFilePath);
  const openFile = useEditorStore((state) => state.openFile);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const setDirty = useEditorStore((state) => state.setDirty);
  const cursorStateByFile = useEditorStore((state) => state.cursorStateByFile);
  const setCursorState = useEditorStore((state) => state.setCursorState);
  const navigateTo = useEditorStore((state) => state.navigateTo);
  const setNavigateTo = useEditorStore((state) => state.setNavigateTo);
  const addToast = useUiStore((state) => state.addToast);
  const setLastSavedAt = useUiStore((state) => state.setLastSavedAt);
  const userRole = useUiStore((state) => state.role);
  const queryClient = useQueryClient();
  const validationAutoRun = useUiStore((state) => state.validationAutoRun);
  const setValidationAutoRun = useUiStore((state) => state.setValidationAutoRun);
  const latestValidationRun = useValidationStore((state) => state.latestRun);
  const setLatestValidationRun = useValidationStore((state) => state.setLatestRun);
  const lastValidationCategories = useValidationStore((state) => state.lastCategories);
  const { theme } = useTheme();
  const [draft, setDraft] = useState("");
  const [findVisible, setFindVisible] = useState(false);
  const [findQuery, setFindQuery] = useState("");
  const [replaceQuery, setReplaceQuery] = useState("");
  const [findRegex, setFindRegex] = useState(false);
  const [quickOpenVisible, setQuickOpenVisible] = useState(false);
  const [quickOpenQuery, setQuickOpenQuery] = useState("");
  const [quickOpenIndex, setQuickOpenIndex] = useState(0);
  const [isEditorExpanded, setIsEditorExpanded] = useState(false);
  const [previewEngine, setPreviewEngine] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState("");
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const findInputRef = useRef<HTMLInputElement | null>(null);
  const quickOpenInputRef = useRef<HTMLInputElement | null>(null);
  const prevActiveTabRef = useRef(activeTab);
  const prevActiveFilePathRef = useRef<string | null>(activeFilePath);
  const navigationDecorationsRef = useRef<string[]>([]);
  const navigationDecorationTimerRef = useRef<number | null>(null);
  const modelId = useMemo(() => extractModelIdFromPath(activeFilePath), [activeFilePath]);
  const editorLanguage = useMemo(() => resolveEditorLanguage(activeFilePath), [activeFilePath]);

  const contentQuery = useQuery({
    queryKey: ["fileContent", currentProjectId, activeFilePath],
    queryFn: () => fetchFileContent(currentProjectId as string, activeFilePath as string),
    enabled: Boolean(currentProjectId && activeFilePath),
  });
  const autocompleteQuery = useQuery({
    queryKey: ["autocomplete", currentProjectId, modelId],
    queryFn: () => fetchProjectAutocomplete(currentProjectId as string, modelId),
    enabled: Boolean(currentProjectId),
  });
  const configChainQuery = useQuery({
    queryKey: ["configChain", currentProjectId, modelId, activeFilePath],
    queryFn: () => fetchModelConfigChain(currentProjectId as string, modelId as string, activeFilePath as string),
    enabled: Boolean(currentProjectId && modelId && activeFilePath),
  });
  const projectTreeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const allProjectFiles = useMemo(() => {
    const root = projectTreeQuery.data;
    if (!root) return [] as string[];
    const files: string[] = [];
    const stack = [root];
    while (stack.length > 0) {
      const current = stack.pop();
      if (!current) continue;
      if (current.type === "file") {
        files.push(current.path);
        continue;
      }
      for (const child of current.children ?? []) {
        stack.push(child);
      }
    }
    return files.sort((a, b) => a.localeCompare(b));
  }, [projectTreeQuery.data]);
  const quickOpenCandidates = useMemo(() => {
    const query = quickOpenQuery.trim().toLowerCase();
    if (!query) return allProjectFiles.slice(0, 100);
    return allProjectFiles.filter((path) => path.toLowerCase().includes(query)).slice(0, 100);
  }, [allProjectFiles, quickOpenQuery]);

  const parametersByName = useMemo(() => {
    const entries = autocompleteQuery.data?.parameters ?? [];
    const map = new Map<
      string,
      {
        name: string;
        path: string;
        domain_type: string | null;
        value_type: string | null;
      }
    >();
    for (const item of entries) {
      map.set(item.name, {
        name: item.name,
        path: item.path,
        domain_type: item.domain_type,
        value_type: item.value_type,
      });
      map.set(item.name.toLowerCase(), {
        name: item.name,
        path: item.path,
        domain_type: item.domain_type,
        value_type: item.value_type,
      });
    }
    return map;
  }, [autocompleteQuery.data?.parameters]);
  const macroNames = useMemo(
    () => new Set((autocompleteQuery.data?.macros ?? []).map((item) => item.name.toLowerCase())),
    [autocompleteQuery.data?.macros],
  );
  const parameterUsages = useMemo(() => {
    const namesFromWorkflow = configChainQuery.data?.sql_metadata?.parameters ?? [];
    const names = namesFromWorkflow.length > 0 ? namesFromWorkflow : parseSqlParameters(draft);
    return names.map((name) => {
      const meta = parametersByName.get(name) ?? parametersByName.get(name.toLowerCase());
      return {
        name,
        domain_type: meta?.domain_type ?? null,
        value_type: meta?.value_type ?? null,
      };
    });
  }, [configChainQuery.data?.sql_metadata?.parameters, draft, parametersByName]);
  const ctes = useMemo(() => {
    const workflowCtes = configChainQuery.data?.sql_metadata?.ctes ?? [];
    if (workflowCtes.length > 0) return workflowCtes;
    return parseSqlCtes(draft);
  }, [configChainQuery.data?.sql_metadata?.ctes, draft]);

  useEffect(() => {
    if (!autocompleteQuery.data) return;
    setDqcrAutocompleteData({
      parameters: autocompleteQuery.data.parameters.map((item) => item.name),
      macros: autocompleteQuery.data.macros.map((item) => item.name),
      configKeys: autocompleteQuery.data.config_keys,
      objects: autocompleteQuery.data.objects ?? [],
      activeModelId: modelId,
    });
  }, [autocompleteQuery.data, modelId]);

  useEffect(() => {
    if (contentQuery.data !== undefined) {
      setDraft(contentQuery.data);
      if (activeFilePath) setDirty(activeFilePath, false);
    }
  }, [contentQuery.data, activeFilePath, setDirty]);

  useEffect(() => {
    const prevTab = prevActiveTabRef.current;
    const editor = editorRef.current;
    if (prevTab === "sql" && activeTab !== "sql" && editor && activeFilePath) {
      setCursorState(activeFilePath, {
        position: editor.getPosition(),
        scrollTop: editor.getScrollTop(),
        scrollLeft: editor.getScrollLeft(),
      });
    }
    prevActiveTabRef.current = activeTab;
  }, [activeFilePath, activeTab, setCursorState]);

  useEffect(() => {
    const prevPath = prevActiveFilePathRef.current;
    const editor = editorRef.current;
    if (activeTab === "sql" && prevPath && prevPath !== activeFilePath && editor) {
      setCursorState(prevPath, {
        position: editor.getPosition(),
        scrollTop: editor.getScrollTop(),
        scrollLeft: editor.getScrollLeft(),
      });
    }
    prevActiveFilePathRef.current = activeFilePath;
  }, [activeFilePath, activeTab, setCursorState]);

  useEffect(() => {
    if (activeTab !== "sql") return;
    const editor = editorRef.current;
    if (!editor || !activeFilePath) return;
    const state = cursorStateByFile[activeFilePath] ?? { position: null, scrollTop: 0, scrollLeft: 0 };
    const timer = window.setTimeout(() => {
      if (state.position) {
        editor.setPosition(state.position);
        editor.revealPositionInCenter(state.position, 0);
      }
      editor.setScrollTop(state.scrollTop);
      editor.setScrollLeft(state.scrollLeft);
    }, 50);
    return () => window.clearTimeout(timer);
  }, [activeFilePath, activeTab, cursorStateByFile]);

  useEffect(() => {
    if (!navigateTo) return;
    if (!activeFilePath || navigateTo.path !== activeFilePath) return;
    if (contentQuery.status !== "success") return;
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor?.getModel();
    if (!editor || !monaco || !model) return;

    if (navigationDecorationTimerRef.current !== null) {
      window.clearTimeout(navigationDecorationTimerRef.current);
      navigationDecorationTimerRef.current = null;
    }
    navigationDecorationsRef.current = editor.deltaDecorations(navigationDecorationsRef.current, []);

    const maxLine = model.getLineCount();
    const line = navigateTo.line ?? 1;
    const targetLine = Math.min(Math.max(1, line), Math.max(1, maxLine));
    editor.revealLineInCenter(targetLine);
    editor.setPosition({ lineNumber: targetLine, column: 1 });
    navigationDecorationsRef.current = editor.deltaDecorations([], [
      {
        range: new monaco.Range(targetLine, 1, targetLine, 1),
        options: {
          isWholeLine: true,
          className: "validate-error-highlight",
          linesDecorationsClassName: "validate-error-gutter",
        },
      },
    ]);
    editor.focus();
    setNavigateTo(null);

    navigationDecorationTimerRef.current = window.setTimeout(() => {
      const currentEditor = editorRef.current;
      if (!currentEditor) return;
      navigationDecorationsRef.current = currentEditor.deltaDecorations(navigationDecorationsRef.current, []);
      navigationDecorationTimerRef.current = null;
    }, 3000);
  }, [activeFilePath, contentQuery.status, navigateTo, setNavigateTo]);

  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor?.getModel();
    if (!editor || !monaco || !model) return;

    const scopedRun = latestValidationRun?.project === currentProjectId ? latestValidationRun : null;
    const rulesForFile =
      scopedRun?.rules.filter(
        (item) => item.file_path === activeFilePath && (item.status === "error" || item.status === "warning"),
      ) ?? [];

    const markers = rulesForFile.map((item) => {
      const lineNumber = Math.max(1, item.line ?? 1);
      return {
        startLineNumber: lineNumber,
        startColumn: 1,
        endLineNumber: lineNumber,
        endColumn: model.getLineMaxColumn(lineNumber),
        severity: item.status === "error" ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
        message: `${item.rule_id}: ${item.message}`,
        source: "validation",
      };
    });
    monaco.editor.setModelMarkers(model, "validation", markers);
  }, [activeFilePath, currentProjectId, draft, latestValidationRun]);

  const saveMutation = useMutation({
    mutationFn: () => saveFileContent(currentProjectId as string, activeFilePath as string, draft),
    onSuccess: async () => {
      if (activeFilePath) setDirty(activeFilePath, false);
      const savedAt = new Date();
      setLastSavedAt(savedAt);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["configChain", currentProjectId, modelId, activeFilePath] }),
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
  const previewMutation = useMutation({
    mutationFn: (engine: string) =>
      fetchBuildPreview(currentProjectId as string, engine, {
        model_id: modelId as string,
        sql_path: activeFilePath as string,
        inline_sql: draft,
      }),
    onSuccess: (payload) => {
      setPreviewEngine(payload.engine);
      setPreviewContent(payload.preview);
    },
    onError: () => {
      addToast("Preview generation failed", "error");
    },
  });

  const findMatches = () => {
    const editor = editorRef.current;
    const model = editor?.getModel();
    if (!editor || !model || !findQuery) return [];
    return model.findMatches(findQuery, true, findRegex, false, null, false, 1000);
  };

  const selectNextMatch = () => {
    const editor = editorRef.current;
    if (!editor) return false;
    const matches = findMatches();
    if (matches.length === 0) {
      addToast("No matches found", "error");
      return false;
    }

    const position = editor.getPosition();
    const currentOffset = position ? editor.getModel()?.getOffsetAt(position) ?? 0 : 0;
    const next = matches.find((item) => {
      const start = editor.getModel()?.getOffsetAt(item.range.getStartPosition()) ?? 0;
      return start > currentOffset;
    });
    const target = next ?? matches[0];
    editor.setSelection(target.range);
    editor.revealRangeInCenter(target.range);
    editor.focus();
    return true;
  };

  const replaceOne = () => {
    const editor = editorRef.current;
    if (!editor) return;
    const selection = editor.getSelection();
    if (selection && !selection.isEmpty()) {
      editor.executeEdits("replace-one", [{ range: selection, text: replaceQuery }]);
      selectNextMatch();
      return;
    }
    if (selectNextMatch()) {
      const selected = editor.getSelection();
      if (selected && !selected.isEmpty()) {
        editor.executeEdits("replace-one", [{ range: selected, text: replaceQuery }]);
      }
    }
  };

  const replaceAll = () => {
    const editor = editorRef.current;
    const model = editor?.getModel();
    if (!editor || !model) return;
    const matches = findMatches();
    if (matches.length === 0) {
      addToast("No matches found", "error");
      return;
    }
    editor.executeEdits(
      "replace-all",
      [...matches].reverse().map((match) => ({
        range: match.range,
        text: replaceQuery,
      })),
    );
    addToast(`Replaced ${matches.length} matches`, "success");
  };

  const applyFormatting = async () => {
    let formatted = formatSqlBasic(draft);
    try {
      const prettier = await import("prettier/standalone");
      const pluginSqlModule = await import("prettier-plugin-sql");
      const pluginSql = (pluginSqlModule as { default?: unknown }).default ?? pluginSqlModule;
      formatted = await prettier.format(draft, {
        parser: "sql",
        plugins: [pluginSql as never],
        keywordCase: "upper",
      });
    } catch {
      // fallback formatter is already applied above
    }
    setDraft(formatted);
    if (activeFilePath) {
      setDirty(activeFilePath, formatted !== (contentQuery.data ?? ""));
    }
    addToast("SQL formatted", "success");
  };

  const handleGoToDefinition = () => {
    const editor = editorRef.current;
    const model = editor?.getModel();
    const position = editor?.getPosition();
    if (!editor || !model || !position) return;

    const word = model.getWordAtPosition(position)?.word;
    if (!word) return;

    const parameterTarget = parametersByName.get(word) ?? parametersByName.get(word.toLowerCase());
    if (parameterTarget?.path) {
      openFile(parameterTarget.path);
      setActiveTab("sql");
      addToast(`Opened ${parameterTarget.path}`, "success");
      return;
    }

    if (macroNames.has(word.toLowerCase())) {
      addToast(`Macro '${word}' is built-in (no local definition file)`, "success");
      return;
    }

    addToast(`Definition not found for '${word}'`, "error");
  };

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const isSave = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s";
      const isFindReplace = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "h";
      const isQuickOpen = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "p";
      const isFormat = (event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "f";
      const isGotoDefinition = event.key === "F12";

      if (isSave && activeFilePath) {
        event.preventDefault();
        saveMutation.mutate();
        return;
      }
      if (isFindReplace) {
        event.preventDefault();
        setFindVisible(true);
        setTimeout(() => findInputRef.current?.focus(), 0);
        return;
      }
      if (isQuickOpen) {
        event.preventDefault();
        setQuickOpenVisible(true);
        setQuickOpenIndex(0);
        setTimeout(() => quickOpenInputRef.current?.focus(), 0);
        return;
      }
      if (isFormat && activeFilePath) {
        event.preventDefault();
        void applyFormatting();
        return;
      }
      if (isGotoDefinition && activeFilePath) {
        event.preventDefault();
        handleGoToDefinition();
      }

      if (quickOpenVisible) {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          setQuickOpenIndex((prev) => Math.min(prev + 1, Math.max(quickOpenCandidates.length - 1, 0)));
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          setQuickOpenIndex((prev) => Math.max(prev - 1, 0));
          return;
        }
        if (event.key === "Enter") {
          event.preventDefault();
          const selected = quickOpenCandidates[quickOpenIndex];
          if (selected) {
            openFile(selected);
            setQuickOpenVisible(false);
            setQuickOpenQuery("");
          }
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          setQuickOpenVisible(false);
          setQuickOpenQuery("");
          return;
        }
      }

      if (findVisible && event.key === "Escape") {
        event.preventDefault();
        setFindVisible(false);
        return;
      }

      if (isEditorExpanded && event.key === "Escape") {
        event.preventDefault();
        setIsEditorExpanded(false);
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === ".") {
        event.preventDefault();
        setIsEditorExpanded((current) => !current);
        return;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [
    activeTab,
    activeFilePath,
    saveMutation,
    draft,
    findQuery,
    findRegex,
    replaceQuery,
    parametersByName,
    macroNames,
    quickOpenVisible,
    quickOpenCandidates,
    quickOpenIndex,
    findVisible,
    isEditorExpanded,
    openFile,
  ]);

  const title = useMemo(() => {
    if (!activeFilePath) return "No file selected";
    return activeFilePath.split("/").pop() ?? activeFilePath;
  }, [activeFilePath]);

  if (!activeFilePath) {
    return (
      <section className="workbench">
        <h1>SQL Editor</h1>
        <p>Select a SQL file in sidebar to start editing.</p>
      </section>
    );
  }

  return (
    <section className={isEditorExpanded ? "workbench workbench-editor-expanded" : "workbench"}>
      <div className="workbench-head">
        <h1>SQL Editor: {title}</h1>
        <button
          type="button"
          className="editor-expand-btn"
          onClick={() => setIsEditorExpanded((current) => !current)}
          aria-label={isEditorExpanded ? "Collapse editor" : "Expand editor"}
          title={isEditorExpanded ? "Collapse editor" : "Expand editor"}
        >
          {isEditorExpanded ? "⤡" : "⤢"}
        </button>
      </div>
      <FileTabs />
      <Breadcrumb path={activeFilePath} />
      {quickOpenVisible ? (
        <div className="sql-quickopen-panel">
          <div className="sql-quickopen-row">
            <input
              ref={quickOpenInputRef}
              className="ui-input"
              placeholder="Quick Open (Ctrl+P)"
              value={quickOpenQuery}
              onChange={(event) => {
                setQuickOpenQuery(event.target.value);
                setQuickOpenIndex(0);
              }}
            />
            <button
              type="button"
              className="action-btn"
              onClick={() => {
                setQuickOpenVisible(false);
                setQuickOpenQuery("");
              }}
            >
              Close
            </button>
          </div>
          <ul className="sql-quickopen-list">
            {quickOpenCandidates.map((filePath, index) => (
              <li key={filePath}>
                <button
                  type="button"
                  className={index === quickOpenIndex ? "sql-quickopen-item sql-quickopen-item-active" : "sql-quickopen-item"}
                  onClick={() => {
                    openFile(filePath);
                    setQuickOpenVisible(false);
                    setQuickOpenQuery("");
                  }}
                >
                  {filePath}
                </button>
              </li>
            ))}
            {quickOpenCandidates.length === 0 ? <li className="sql-quickopen-empty">No files found.</li> : null}
          </ul>
        </div>
      ) : null}
      {findVisible ? (
        <div className="sql-find-panel">
          <div className="sql-find-row">
            <input
              ref={findInputRef}
              className="ui-input"
              placeholder="Find (Ctrl+H)"
              value={findQuery}
              onChange={(event) => setFindQuery(event.target.value)}
            />
            <input
              className="ui-input"
              placeholder="Replace"
              value={replaceQuery}
              onChange={(event) => setReplaceQuery(event.target.value)}
            />
            <label className="sql-find-flag">
              <input type="checkbox" checked={findRegex} onChange={(event) => setFindRegex(event.target.checked)} />
              Regex
            </label>
            <button type="button" className="action-btn" onClick={selectNextMatch}>
              Find Next
            </button>
            <button type="button" className="action-btn" onClick={replaceOne}>
              Replace
            </button>
            <button type="button" className="action-btn" onClick={replaceAll}>
              Replace All
            </button>
            <button type="button" className="action-btn" onClick={() => setFindVisible(false)}>
              Close
            </button>
          </div>
        </div>
      ) : null}
      <div className={isEditorExpanded ? "sql-layout sql-layout-expanded" : "sql-layout"}>
        <div className={isEditorExpanded ? "sql-editor-panel sql-editor-panel-expanded" : "sql-editor-panel"}>
          <div className="sql-editor-panel-head">
            <div className="sql-editor-panel-copy">
              <span className="sql-editor-panel-eyebrow">{isEditorExpanded ? "Expanded workspace" : "Query workspace"}</span>
              <strong className="sql-editor-panel-title">{title}</strong>
            </div>
            <button
              type="button"
              className="editor-expand-btn"
              onClick={() => setIsEditorExpanded((current) => !current)}
              aria-label={isEditorExpanded ? "Collapse editor" : "Expand editor"}
              title={isEditorExpanded ? "Collapse editor" : "Expand editor"}
            >
              {isEditorExpanded ? "⤡" : "⤢"}
            </button>
          </div>
          <Editor
            height={isEditorExpanded ? "76vh" : "420px"}
            beforeMount={configureDqcrMonaco}
            onMount={(editor, monaco) => {
              editorRef.current = editor;
              monacoRef.current = monaco;
            }}
            language={editorLanguage}
            theme={getDqcrTheme(theme)}
            value={draft}
            options={{
              minimap: { enabled: false },
              fontSize: 11.5,
              lineHeight: 19,
              fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", "Courier New", monospace',
              automaticLayout: true,
              wordWrap: "on",
              scrollBeyondLastLine: false,
            }}
            onChange={(value) => {
              const nextValue = value ?? "";
              setDraft(nextValue);
              const editor = editorRef.current;
              if (editor && navigationDecorationsRef.current.length > 0) {
                navigationDecorationsRef.current = editor.deltaDecorations(navigationDecorationsRef.current, []);
              }
              setDirty(activeFilePath, nextValue !== (contentQuery.data ?? ""));
            }}
          />
        </div>
        {configChainQuery.data ? (
          <PriorityChainPanel
            levels={configChainQuery.data.levels}
            resolved={configChainQuery.data.resolved}
            parameterUsages={parameterUsages}
            ctes={ctes}
            cteDefault={configChainQuery.data.cte_settings.default}
            cteByContext={configChainQuery.data.cte_settings.by_context}
            inlineCteConfigs={configChainQuery.data.sql_metadata?.inline_cte_configs ?? {}}
            generatedOutputs={configChainQuery.data.generated_outputs}
            previewLoading={previewMutation.isPending}
            previewEngine={previewEngine}
            previewContent={previewContent}
            onPreview={(engine) => previewMutation.mutate(engine)}
            dataSource={configChainQuery.data.data_source}
            fallback={configChainQuery.data.fallback}
          />
        ) : (
          <aside className="config-chain-panel">
            <h2>@config Priority Chain</h2>
            <p className="config-chain-placeholder">
              {modelId ? "No config chain data yet." : "Open a file inside model/* to load config chain."}
            </p>
          </aside>
        )}
      </div>
      <div className="sql-actions">
        <button type="button" className="action-btn action-btn-primary" onClick={() => saveMutation.mutate()}>
          Save (Ctrl+S)
        </button>
        <button type="button" className="action-btn" onClick={applyFormatting}>
          Format (Ctrl+Shift+F)
        </button>
        <label className="sql-auto-validate-toggle">
          <input
            type="checkbox"
            checked={validationAutoRun}
            onChange={(event) => setValidationAutoRun(event.target.checked)}
          />
          Auto validate on save
        </label>
        <span>{saveMutation.isSuccess ? "Saved" : "Editing"}</span>
      </div>
    </section>
  );
}
