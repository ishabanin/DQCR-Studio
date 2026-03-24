import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";

import {
  fetchFileContent,
  fetchProjectAutocomplete,
  fetchProjectTree,
  runProjectValidation,
  saveFileContent,
} from "../../api/projects";
import { useTheme } from "../../app/providers/ThemeProvider";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useSqlTabsStore } from "../../app/store/sqlTabsStore";
import { useUiStore } from "../../app/store/uiStore";
import { useValidationStore } from "../../app/store/validationStore";
import { configureDqcrMonaco, DQCR_LANGUAGE_ID, getDqcrTheme, setDqcrAutocompleteData } from "./dqcrLanguage";
import SqlMetaPanel from "./components/SqlMetaPanel";
import SqlFullscreenOverlay from "./components/SqlFullscreenOverlay";
import SqlModeBar from "./components/SqlModeBar";
import SqlTabBar from "./components/SqlTabBar";
import { useSqlFullscreen } from "./hooks/useSqlFullscreen";
import { useSqlRenderedContent } from "./hooks/useSqlRenderedContent";
import { useSqlStepMeta } from "./hooks/useSqlStepMeta";
import { useSqlViewMode } from "./hooks/useSqlViewMode";

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

export default function SqlEditorScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeTab = useEditorStore((state) => state.activeTab);
  const setActiveFile = useEditorStore((state) => state.setActiveFile);
  const openFile = useEditorStore((state) => state.openFile);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const cursorStateByFile = useEditorStore((state) => state.cursorStateByFile);
  const setCursorState = useEditorStore((state) => state.setCursorState);
  const navigateTo = useEditorStore((state) => state.navigateTo);
  const setNavigateTo = useEditorStore((state) => state.setNavigateTo);
  const setLineageTarget = useEditorStore((state) => state.setLineageTarget);
  const sqlTabs = useSqlTabsStore((state) => state.tabs);
  const activeSqlTabId = useSqlTabsStore((state) => state.activeTabId);
  const setActiveSqlTab = useSqlTabsStore((state) => state.setActiveTab);
  const closeSqlTab = useSqlTabsStore((state) => state.closeTab);
  const openSqlTab = useSqlTabsStore((state) => state.openTab);
  const setSqlTabDirty = useSqlTabsStore((state) => state.setTabDirty);
  const updateSqlTabScroll = useSqlTabsStore((state) => state.updateTabScroll);
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
  const activeSqlTab = useMemo(() => sqlTabs.find((tab) => tab.id === activeSqlTabId) ?? null, [activeSqlTabId, sqlTabs]);
  const activeFilePath = activeSqlTab?.filePath ?? null;
  const [draft, setDraft] = useState("");
  const [findVisible, setFindVisible] = useState(false);
  const [findQuery, setFindQuery] = useState("");
  const [replaceQuery, setReplaceQuery] = useState("");
  const [findRegex, setFindRegex] = useState(false);
  const [quickOpenVisible, setQuickOpenVisible] = useState(false);
  const [quickOpenQuery, setQuickOpenQuery] = useState("");
  const [quickOpenIndex, setQuickOpenIndex] = useState(0);
  const [isEditorExpanded, setIsEditorExpanded] = useState(false);
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const modeViewStateRef = useRef<Record<string, Monaco.editor.ICodeEditorViewState | null>>({});
  const findInputRef = useRef<HTMLInputElement | null>(null);
  const quickOpenInputRef = useRef<HTMLInputElement | null>(null);
  const [pendingCloseTabId, setPendingCloseTabId] = useState<string | null>(null);
  const activeSqlTabIdRef = useRef<string | null>(activeSqlTabId);
  const prevActiveTabRef = useRef(activeTab);
  const prevActiveFilePathRef = useRef<string | null>(activeFilePath);
  const navigationDecorationsRef = useRef<string[]>([]);
  const navigationDecorationTimerRef = useRef<number | null>(null);
  const modelId = useMemo(() => extractModelIdFromPath(activeFilePath), [activeFilePath]);
  const editorLanguage = useMemo(() => resolveEditorLanguage(activeFilePath), [activeFilePath]);
  const { mode, setMode, selectedTool, setSelectedTool } = useSqlViewMode(activeFilePath);
  const sqlStepMeta = useSqlStepMeta(currentProjectId, modelId, activeFilePath);
  const pendingCloseTab = useMemo(() => sqlTabs.find((tab) => tab.id === pendingCloseTabId) ?? null, [pendingCloseTabId, sqlTabs]);
  const prevFullscreenRef = useRef(false);
  const prevSqlFilePathRef = useRef<string | null>(null);
  const { isFullscreen, enter: enterFullscreen, exit: exitFullscreen } = useSqlFullscreen({
    enabled: Boolean(activeFilePath),
    onEnter: () => setIsEditorExpanded(false),
  });

  useEffect(() => {
    activeSqlTabIdRef.current = activeSqlTabId;
  }, [activeSqlTabId]);

  useEffect(() => {
    if (prevFullscreenRef.current && !isFullscreen) {
      window.setTimeout(() => {
        editorRef.current?.layout();
      }, 0);
    }
    prevFullscreenRef.current = isFullscreen;
  }, [isFullscreen]);

  const openPathInSql = useCallback((path: string) => {
    const result = openSqlTab(path);
    if (!result.ok && result.reason === "limit") {
      addToast("Достигнут лимит открытых файлов (20). Закройте ненужные вкладки.", "error");
      return false;
    }
    openFile(path);
    setActiveTab("sql");
    return true;
  }, [addToast, openFile, openSqlTab, setActiveTab]);

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
  const workflowTools = useMemo(() => {
    const toolsRaw = sqlStepMeta.workflow?.tools;
    if (!Array.isArray(toolsRaw)) return [] as string[];
    return toolsRaw.filter((item): item is string => typeof item === "string");
  }, [sqlStepMeta.workflow]);
  const renderedSql = useSqlRenderedContent(sqlStepMeta.step, mode, selectedTool);
  const editorContent = mode === "source" ? draft : renderedSql ?? "";

  useEffect(() => {
    if (prevSqlFilePathRef.current !== activeFilePath) {
      prevSqlFilePathRef.current = activeFilePath;
      if (mode !== "source") {
        setMode("source");
      }
    }
  }, [activeFilePath, mode, setMode]);

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
    if (contentQuery.data === undefined) return;
    if (activeSqlTab?.isDirty) return;
    setDraft(contentQuery.data);
  }, [activeSqlTab?.id, activeSqlTab?.isDirty, contentQuery.data]);

  useEffect(() => {
    setActiveFile(activeFilePath);
  }, [activeFilePath, setActiveFile]);

  useEffect(() => {
    if (mode === "source") return;
    if (workflowTools.length === 0) return;
    if (selectedTool && workflowTools.includes(selectedTool)) return;
    setSelectedTool(workflowTools[0]);
  }, [mode, selectedTool, setSelectedTool, workflowTools]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !activeFilePath) return;
    const key = `${activeFilePath}:${mode}`;
    const timer = window.setTimeout(() => {
      const state = modeViewStateRef.current[key];
      if (state) {
        editor.restoreViewState(state);
      }
      editor.focus();
    }, 20);
    return () => window.clearTimeout(timer);
  }, [activeFilePath, mode, editorContent]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !activeFilePath) return;
    const key = `${activeFilePath}:${mode}`;
    return () => {
      modeViewStateRef.current[key] = editor.saveViewState();
    };
  }, [activeFilePath, mode]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.updateOptions({ readOnly: mode !== "source" });
  }, [mode]);

  useEffect(() => {
    const prevTab = prevActiveTabRef.current;
    const editor = editorRef.current;
    if (prevTab === "sql" && activeTab !== "sql" && editor && activeFilePath) {
      setCursorState(activeFilePath, {
        position: editor.getPosition(),
        scrollTop: editor.getScrollTop(),
        scrollLeft: editor.getScrollLeft(),
      });
      if (activeSqlTab) {
        updateSqlTabScroll(activeSqlTab.id, editor.getScrollTop());
      }
    }
    prevActiveTabRef.current = activeTab;
  }, [activeFilePath, activeSqlTab, activeTab, setCursorState, updateSqlTabScroll]);

  useEffect(() => {
    const prevPath = prevActiveFilePathRef.current;
    const editor = editorRef.current;
    if (activeTab === "sql" && prevPath && prevPath !== activeFilePath && editor) {
      setCursorState(prevPath, {
        position: editor.getPosition(),
        scrollTop: editor.getScrollTop(),
        scrollLeft: editor.getScrollLeft(),
      });
      if (activeSqlTab) {
        updateSqlTabScroll(activeSqlTab.id, editor.getScrollTop());
      }
    }
    prevActiveFilePathRef.current = activeFilePath;
  }, [activeFilePath, activeSqlTab, activeTab, setCursorState, updateSqlTabScroll]);

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
      const tabScroll = activeSqlTab?.scrollTop ?? state.scrollTop;
      editor.setScrollTop(tabScroll);
      editor.setScrollLeft(state.scrollLeft);
    }, 50);
    return () => window.clearTimeout(timer);
  }, [activeFilePath, activeSqlTab, activeTab, cursorStateByFile]);

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
    mutationFn: (content: string) => saveFileContent(currentProjectId as string, activeFilePath as string, content),
    onSuccess: async (_, savedContent) => {
      if (currentProjectId && activeFilePath) {
        queryClient.setQueryData(["fileContent", currentProjectId, activeFilePath], savedContent);
      }
      setDraft(savedContent);
      if (activeSqlTab) setSqlTabDirty(activeSqlTab.id, false);
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
    if (activeSqlTab) {
      setSqlTabDirty(activeSqlTab.id, formatted !== (contentQuery.data ?? ""));
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
      if (openPathInSql(parameterTarget.path)) {
        addToast(`Opened ${parameterTarget.path}`, "success");
      }
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

      if (isSave && activeFilePath && mode === "source") {
        event.preventDefault();
        saveMutation.mutate(draft);
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
      if (isFormat && activeFilePath && mode === "source") {
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
            openPathInSql(selected);
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
        if (isFullscreen) return;
        event.preventDefault();
        setFindVisible(false);
        return;
      }

      if (isEditorExpanded && event.key === "Escape") {
        if (isFullscreen) return;
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
    activeFilePath,
    saveMutation,
    draft,
    parametersByName,
    macroNames,
    quickOpenVisible,
    quickOpenCandidates,
    quickOpenIndex,
    findVisible,
    isFullscreen,
    isEditorExpanded,
    mode,
    openPathInSql,
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
      <SqlTabBar
        tabs={sqlTabs}
        activeTabId={activeSqlTabId}
        onSelectTab={(tabId) => {
          setActiveSqlTab(tabId);
        }}
        onRequestClose={(tabId) => {
          const tab = sqlTabs.find((item) => item.id === tabId);
          if (!tab) return;
          if (!tab.isDirty) {
            closeSqlTab(tabId);
            return;
          }
          setPendingCloseTabId(tabId);
        }}
      />
      <Breadcrumb path={activeFilePath} />
      <SqlModeBar
        mode={mode}
        onModeChange={setMode}
        tools={workflowTools}
        selectedTool={selectedTool}
        onToolChange={setSelectedTool}
        hasWorkflowCache={sqlStepMeta.status === "ok"}
        onToggleFullscreen={() => {
          if (isFullscreen) exitFullscreen();
          else enterFullscreen();
        }}
      />
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
                    openPathInSql(filePath);
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
          <div className={isFullscreen ? "sql-editor-canvas sql-editor--fullscreen" : "sql-editor-canvas"}>
            <Editor
              key={`${activeFilePath}:${mode}`}
              height={isFullscreen ? "100vh" : isEditorExpanded ? "76vh" : "420px"}
              beforeMount={configureDqcrMonaco}
              onMount={(editor, monaco) => {
                editorRef.current = editor;
                monacoRef.current = monaco;
                editor.onDidScrollChange(() => {
                  const currentTabId = activeSqlTabIdRef.current;
                  if (!currentTabId) return;
                  updateSqlTabScroll(currentTabId, editor.getScrollTop());
                });
              }}
              path={`${activeFilePath}::${mode}`}
              language={editorLanguage}
              theme={getDqcrTheme(theme)}
              value={editorContent}
              options={{
                minimap: { enabled: false },
                fontSize: 11.5,
                lineHeight: 19,
                fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", "Courier New", monospace',
                automaticLayout: true,
                wordWrap: "on",
                scrollBeyondLastLine: false,
                readOnly: mode !== "source",
              }}
              onChange={(value) => {
                if (mode !== "source") return;
                const nextValue = value ?? "";
                setDraft(nextValue);
                const editor = editorRef.current;
                if (editor && navigationDecorationsRef.current.length > 0) {
                  navigationDecorationsRef.current = editor.deltaDecorations(navigationDecorationsRef.current, []);
                }
                if (activeSqlTab) {
                  setSqlTabDirty(activeSqlTab.id, nextValue !== (contentQuery.data ?? ""));
                }
              }}
            />
            {isFullscreen && activeSqlTab ? (
              <SqlFullscreenOverlay
                fileName={activeSqlTab.fileName}
                isDirty={activeSqlTab.isDirty}
                mode={mode}
                onModeChange={setMode}
                tools={workflowTools}
                selectedTool={selectedTool}
                onToolChange={setSelectedTool}
                onSave={() => {
                  if (mode !== "source") return;
                  saveMutation.mutate(draft);
                }}
                onFormat={() => {
                  if (mode !== "source") return;
                  void applyFormatting();
                }}
                onExit={exitFullscreen}
              />
            ) : null}
          </div>
          {mode !== "source" && sqlStepMeta.status === "ok" && !editorContent ? (
            <p className="sql-mode-placeholder sql-mode-placeholder-under-editor">Нет SQL для выбранного tool в этом режиме.</p>
          ) : null}
        </div>
        {!isFullscreen ? (
          <SqlMetaPanel
          filePath={activeFilePath}
          modelId={modelId}
          allProjectFiles={allProjectFiles}
          step={sqlStepMeta.step}
          workflow={sqlStepMeta.workflow}
          status={sqlStepMeta.status}
          workflowStatus={sqlStepMeta.workflowStatus}
          isLoading={sqlStepMeta.isLoading}
          onOpenFile={(path) => {
            openPathInSql(path);
          }}
          onOpenLineage={(dependency) => {
            setActiveTab("lineage");
            setNavigateTo(null);
            setLineageTarget({ modelId, nodePath: dependency });
          }}
          />
        ) : null}
      </div>
      {mode === "source" ? (
        <div className="sql-actions">
          <button type="button" className="action-btn action-btn-primary" onClick={() => saveMutation.mutate(draft)}>
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
      ) : null}
      {pendingCloseTab ? (
        <div className="sql-close-dialog-overlay" role="dialog" aria-modal="true">
          <div className="sql-close-dialog">
            <h3>Несохранённые изменения</h3>
            <p>Файл {pendingCloseTab.fileName} имеет несохранённые изменения. Закрыть без сохранения?</p>
            <div className="sql-close-dialog-actions">
              <button
                type="button"
                className="action-btn action-btn-primary"
                onClick={() => {
                  if (activeSqlTabId !== pendingCloseTab.id) {
                    setActiveSqlTab(pendingCloseTab.id);
                    setPendingCloseTabId(null);
                    addToast("Сначала сохраните файл из активной вкладки", "error");
                    return;
                  }
                  saveMutation.mutate(draft, {
                    onSuccess: () => {
                      closeSqlTab(pendingCloseTab.id);
                      setPendingCloseTabId(null);
                    },
                  });
                }}
              >
                Сохранить
              </button>
              <button
                type="button"
                className="action-btn"
                onClick={() => {
                  closeSqlTab(pendingCloseTab.id);
                  setPendingCloseTabId(null);
                }}
              >
                Не сохранять
              </button>
              <button type="button" className="action-btn" onClick={() => setPendingCloseTabId(null)}>
                Отмена
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
