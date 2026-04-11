import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import "reactflow/dist/style.css";

import {
  fetchModelWorkflowGraph,
  fetchModelWorkflowDiagnostics,
  fetchModelWorkflowStepDetail,
  fetchModelLineage,
  fetchProjectTree,
  fetchProjectWorkflowStatus,
  rebuildModelWorkflow,
  FileNode,
  LineageNode,
  WorkflowExecutionStep,
} from "../../api/projects";
import { useContextStore } from "../../app/store/contextStore";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import DagGraph, { DagGraphHandle } from "./DagGraph";
import "./lineage.css";
import { DetailPanel } from "./components/DetailPanel";
import { ExecutionDetailPanel } from "./components/ExecutionDetailPanel";
import { FallbackBanner } from "./components/FallbackBanner";
import { FilterNote } from "./components/FilterNote";
import { GraphArea } from "./components/GraphArea";
import { LineageHeader } from "./components/LineageHeader";
import { LineageSummary } from "./components/LineageSummary";
import { LineageToolbar } from "./components/LineageToolbar";
import { computeVisibleNodes, countNodeCtes, formatNodePath, getConnectionCounts, nodeMatchesSearch } from "./lineageUtils";
import { WorkflowDiagnosticsPanel } from "../../shared/components/WorkflowDiagnosticsPanel";

type LineageViewMode = "horizontal" | "vertical" | "compact";
type GraphKind = "lineage" | "execution";

const VIEW_MODE_KEY = "dqcr_lineage_viewmode";
const GRAPH_KIND_KEY = "dqcr_lineage_graphkind";
const EXECUTION_TOOL_KEY = "dqcr_execution_tool";

function findModelIds(tree: FileNode): string[] {
  const rootChildren = tree.children ?? [];
  const modelRoot = rootChildren.find(
    (child) => child.type === "directory" && ["model", "models"].includes(child.name.toLowerCase()),
  );
  if (!modelRoot || !modelRoot.children) return [];
  return modelRoot.children.filter((child) => child.type === "directory").map((child) => child.name);
}

function LineageSkeleton() {
  const rows = [3, 4, 2];

  return (
    <div className="lg-loading-graph">
      <div className="lg-loading-skeleton-row">
        {rows.map((rowCount, index) => (
          <div key={rowCount + index} className="lg-loading-skeleton-row">
            <div className="lg-loading-node">
              <div className="lg-loading-node-head">
                <div className="lg-skeleton" style={{ height: 12, width: 80, marginBottom: 5 }} />
                <div className="lg-skeleton" style={{ height: 16, width: 64, borderRadius: 20 }} />
              </div>
              <div className="lg-loading-node-body">
                {Array.from({ length: rowCount }).map((_, rowIndex) => (
                  <div
                    key={rowIndex}
                    className="lg-skeleton"
                    style={{ height: 20, borderRadius: 4, marginBottom: rowIndex < rowCount - 1 ? 4 : 0 }}
                  />
                ))}
              </div>
            </div>
            {index < rows.length - 1 ? (
              <div className="lg-loading-edge">
                <div className="lg-loading-edge-line" />
                <span className="lg-loading-edge-arrow">▶</span>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function ShellState({
  icon,
  title,
  description,
  actions,
  danger = false,
}: {
  icon: string;
  title: string;
  description: React.ReactNode;
  actions?: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <div className="lg-state-block">
      <div className={danger ? "lg-state-icon lg-state-icon-danger" : "lg-state-icon"}>{icon}</div>
      <div className="lg-state-title">{title}</div>
      <div className="lg-state-desc">{description}</div>
      {actions}
    </div>
  );
}

function LoadingShell() {
  return (
    <div className="lg-loading-shell">
      <div className="lg-header">
        <div className="lg-header-top">
          <div className="lg-skeleton" style={{ height: 16, width: 220 }} />
        </div>
        <div className="lg-pills">
          <div className="lg-skeleton" style={{ height: 20, width: 80, borderRadius: 20 }} />
          <div className="lg-skeleton" style={{ height: 20, width: 100, borderRadius: 20 }} />
        </div>
      </div>
      <div className="lg-loading-toolbar">
        <div className="lg-skeleton" style={{ height: 26, width: 160, borderRadius: 5 }} />
        <div className="lg-skeleton" style={{ height: 26, width: 240, borderRadius: 5 }} />
        <div className="lg-skeleton" style={{ height: 26, width: 200, borderRadius: 5 }} />
        <div className="lg-skeleton" style={{ height: 26, width: 100, borderRadius: 5, marginLeft: "auto" }} />
      </div>
      <LineageSkeleton />
    </div>
  );
}

export default function LineageScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeContext = useContextStore((state) => state.activeContext);
  const activeContexts = useContextStore((state) => state.activeContexts);
  const multiMode = useContextStore((state) => state.multiMode);
  const openFile = useEditorStore((state) => state.openFile);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const lineageModelId = useEditorStore((state) => state.lineageModelId);
  const lineageNodePath = useEditorStore((state) => state.lineageNodePath);
  const clearLineageNodePath = useEditorStore((state) => state.clearLineageNodePath);
  const addToast = useUiStore((state) => state.addToast);

  const [modelId, setModelId] = useState<string>("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [graphKind, setGraphKind] = useState<GraphKind>(() => {
    const stored = window.localStorage.getItem(GRAPH_KIND_KEY);
    return stored === "execution" ? "execution" : "lineage";
  });
  const [viewMode, setViewMode] = useState<LineageViewMode>(() => {
    const stored = window.localStorage.getItem(VIEW_MODE_KEY);
    return stored === "vertical" || stored === "compact" || stored === "horizontal" ? stored : "horizontal";
  });
  const [searchValue, setSearchValue] = useState("");
  const [selectedTool, setSelectedTool] = useState<string>(() => window.localStorage.getItem(EXECUTION_TOOL_KEY) || "all_tools");

  const graphExportRef = useRef<HTMLDivElement | null>(null);
  const dagGraphRef = useRef<DagGraphHandle | null>(null);

  const treeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const workflowStatusQuery = useQuery({
    queryKey: ["workflowStatus", currentProjectId],
    queryFn: () => fetchProjectWorkflowStatus(currentProjectId as string),
    enabled: Boolean(currentProjectId),
    refetchInterval: currentProjectId ? 10000 : false,
  });

  const modelIds = useMemo(() => {
    if (!treeQuery.data) return [];
    return findModelIds(treeQuery.data);
  }, [treeQuery.data]);

  useEffect(() => {
    if (!modelIds.length) {
      setModelId("");
      return;
    }
    if (lineageModelId && modelIds.includes(lineageModelId) && lineageModelId !== modelId) {
      setModelId(lineageModelId);
      return;
    }
    if (!modelIds.includes(modelId)) {
      setModelId(modelIds[0]);
    }
  }, [modelIds, modelId, lineageModelId]);

  const lineageQuery = useQuery({
    queryKey: ["lineage", currentProjectId, modelId, multiMode ? "all" : activeContext],
    queryFn: () => fetchModelLineage(currentProjectId as string, modelId, multiMode ? undefined : activeContext),
    enabled: Boolean(currentProjectId && modelId && graphKind === "lineage"),
  });

  const executionGraphQuery = useQuery({
    queryKey: ["workflowGraph", currentProjectId, modelId],
    queryFn: () => fetchModelWorkflowGraph(currentProjectId as string, modelId),
    enabled: Boolean(currentProjectId && modelId && graphKind === "execution"),
  });

  const selectedExecutionStep = useMemo(() => {
    const nodes = executionGraphQuery.data?.nodes ?? [];
    if (!selectedNodeId) return null;
    return nodes.find((node) => node.step_id === selectedNodeId) ?? null;
  }, [executionGraphQuery.data?.nodes, selectedNodeId]);

  const executionNodes = executionGraphQuery.data?.nodes ?? [];

  const executionStepDetailQuery = useQuery({
    queryKey: ["workflowStepDetail", currentProjectId, modelId, selectedExecutionStep?.step_id ?? ""],
    queryFn: () => fetchModelWorkflowStepDetail(currentProjectId as string, modelId, selectedExecutionStep?.step_id ?? ""),
    enabled: Boolean(currentProjectId && modelId && graphKind === "execution" && selectedExecutionStep?.step_id),
  });

  const modelDiagnosticsQuery = useQuery({
    queryKey: ["workflowDiagnostics", currentProjectId, modelId],
    queryFn: () => fetchModelWorkflowDiagnostics(currentProjectId as string, modelId),
    enabled: Boolean(currentProjectId && modelId),
  });

  const rebuildMutation = useMutation({
    mutationFn: async () => {
      if (!currentProjectId) return;
      const models = workflowStatusQuery.data?.models ?? [];
      const targetModels = modelId
        ? models.filter((item) => item.model_id === modelId && (item.status === "stale" || item.status === "error"))
        : models.filter((item) => item.status === "stale" || item.status === "error");
      const modelIdsToRebuild =
        targetModels.length > 0 ? targetModels.map((item) => item.model_id) : modelId ? [modelId] : [];
      await Promise.all(modelIdsToRebuild.map((targetModelId) => rebuildModelWorkflow(currentProjectId, targetModelId)));
    },
    onSuccess: () => {
      addToast("Workflow rebuild started", "info");
      workflowStatusQuery.refetch();
    },
    onError: () => {
      addToast("Workflow rebuild failed", "error");
    },
  });

  const executionNodesAsLineage = useMemo<LineageNode[]>(() => {
    const nodes = executionGraphQuery.data?.nodes ?? [];
    return nodes.map((step) => {
      const queryName = step.has_sql_model ? (step.name && step.name.endsWith(".sql") ? step.name : `${step.name || step.step_id}.sql`) : "";
      const parameterName = step.has_param_model && step.name ? step.name : "";
      const semanticTokens = [
        `scope:${step.step_scope}`,
        `context:${step.context}`,
        ...(Array.isArray(step.tools) ? step.tools.map((tool) => `tool:${tool}`) : ["tool:all_tools"]),
      ];
      return {
        id: step.step_id,
        name: step.name || step.step_id,
        path: step.folder ? `model/${modelId}/workflow/${step.folder}` : `workflow/steps/${step.step_id}`,
        materialized: step.step_scope,
        enabled_contexts: step.context === "all" ? null : [step.context],
        queries: queryName ? [queryName] : [],
        parameters: parameterName ? [parameterName, ...semanticTokens] : semanticTokens,
        ctes: [],
      };
    });
  }, [executionGraphQuery.data?.nodes, modelId]);

  const executionToolsMap = useMemo(
    () =>
      Object.fromEntries(
        (executionGraphQuery.data?.nodes ?? []).map((node) => [node.step_id, Array.isArray(node.tools) ? node.tools : null] as const),
      ) as Record<string, string[] | null>,
    [executionGraphQuery.data?.nodes],
  );

  const executionToolOptions = useMemo(() => {
    const counters = executionGraphQuery.data?.summary.tools ?? {};
    return Object.keys(counters)
      .filter((tool) => tool !== "all_tools")
      .sort((a, b) => a.localeCompare(b));
  }, [executionGraphQuery.data?.summary.tools]);

  useEffect(() => {
    if (graphKind !== "execution") return;
    if (selectedTool === "all_tools") return;
    if (executionToolOptions.includes(selectedTool)) return;
    setSelectedTool("all_tools");
    window.localStorage.setItem(EXECUTION_TOOL_KEY, "all_tools");
  }, [graphKind, selectedTool, executionToolOptions]);

  const allNodes = useMemo(
    () => (graphKind === "lineage" ? lineageQuery.data?.nodes ?? [] : executionNodesAsLineage),
    [graphKind, lineageQuery.data?.nodes, executionNodesAsLineage],
  );
  const allEdges = useMemo(
    () => (graphKind === "lineage" ? lineageQuery.data?.edges ?? [] : executionGraphQuery.data?.edges ?? []),
    [graphKind, lineageQuery.data?.edges, executionGraphQuery.data?.edges],
  );
  const selectedContexts = useMemo(
    () => (multiMode ? activeContexts : activeContext ? [activeContext] : []),
    [activeContext, activeContexts, multiMode],
  );

  const enabledContextsMap = useMemo(
    () =>
      Object.fromEntries(allNodes.map((node) => [node.id, node.enabled_contexts] as const)) as Record<string, string[] | null>,
    [allNodes],
  );

  const visibleIds = useMemo(() => {
    if (graphKind !== "execution") {
      return computeVisibleNodes(allNodes, searchValue, selectedContexts, enabledContextsMap);
    }

    const visible = new Set<string>();
    for (const node of allNodes) {
      const enabledContexts = enabledContextsMap[node.id];
      if (enabledContexts !== null && enabledContexts !== undefined && selectedContexts.length > 0) {
        const hasContext = selectedContexts.some((contextId) => enabledContexts.includes(contextId));
        if (!hasContext) continue;
      }

      if (selectedTool !== "all_tools") {
        const tools = executionToolsMap[node.id];
        if (Array.isArray(tools) && tools.length > 0 && !tools.includes(selectedTool)) continue;
      }

      if (!nodeMatchesSearch(node, searchValue)) continue;
      visible.add(node.id);
    }
    return visible;
  }, [graphKind, allNodes, searchValue, selectedContexts, enabledContextsMap, executionToolsMap, selectedTool]);

  const visibleNodes = useMemo(() => allNodes.filter((node) => visibleIds.has(node.id)), [allNodes, visibleIds]);
  const visibleEdges = useMemo(
    () => allEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    [allEdges, visibleIds],
  );

  const searchHidden = useMemo(
    () =>
      allNodes.filter((node) => {
        const matchesSearch = nodeMatchesSearch(node, searchValue);
        const visible = visibleIds.has(node.id);
        return !visible && !matchesSearch;
      }).length,
    [allNodes, searchValue, visibleIds],
  );

  const contextHidden = useMemo(
    () =>
      allNodes.filter((node) => {
        const enabled = enabledContextsMap[node.id];
        if (enabled === null || enabled === undefined || selectedContexts.length === 0) return false;
        return !selectedContexts.some((contextId) => enabled.includes(contextId));
      }).length,
    [allNodes, enabledContextsMap, selectedContexts],
  );

  const toolHidden = useMemo(
    () =>
      graphKind !== "execution" || selectedTool === "all_tools"
        ? 0
        : allNodes.filter((node) => {
            const tools = executionToolsMap[node.id];
            if (!Array.isArray(tools) || tools.length === 0) return false;
            return !tools.includes(selectedTool);
          }).length,
    [graphKind, selectedTool, allNodes, executionToolsMap],
  );

  const overlayHidden = contextHidden + toolHidden;
  const isFiltered = searchValue.trim().length > 0 || overlayHidden > 0;

  useEffect(() => {
    if (lineageNodePath && visibleNodes.length > 0) {
      const normalizedTarget = lineageNodePath.toLowerCase();
      const matchedNode = visibleNodes.find((node) => node.path.toLowerCase() === normalizedTarget);
      if (matchedNode) {
        setSelectedNodeId(matchedNode.id);
        clearLineageNodePath();
        return;
      }
    }

    if (!visibleNodes.length) {
      setSelectedNodeId(null);
      return;
    }

    if (selectedNodeId && visibleNodes.some((node) => node.id === selectedNodeId)) {
      return;
    }

    setSelectedNodeId(visibleNodes[0].id);
  }, [visibleNodes, selectedNodeId, lineageNodePath, clearLineageNodePath]);

  const selectedNode = useMemo(
    () => visibleNodes.find((node) => node.id === selectedNodeId) ?? null,
    [visibleNodes, selectedNodeId],
  );

  const connectionCounts = useMemo(() => getConnectionCounts(selectedNodeId, allEdges), [selectedNodeId, allEdges]);

  const activeWorkflowModelState = useMemo(() => {
    const models = workflowStatusQuery.data?.models ?? [];
    if (modelId) {
      const selected = models.find((item) => item.model_id === modelId);
      if (selected) return selected;
    }
    return models[0] ?? null;
  }, [modelId, workflowStatusQuery.data?.models]);

  const workflowStatus = activeWorkflowModelState?.status ?? null;
  const source = activeWorkflowModelState?.source ?? null;
  const effectiveSource = (graphKind === "execution" ? executionGraphQuery.data?.source : null) ?? source;
  const effectiveWorkflowStatus = (graphKind === "execution" ? executionGraphQuery.data?.status : null) ?? workflowStatus;

  const handleViewMode = (mode: LineageViewMode) => {
    setViewMode(mode);
    window.localStorage.setItem(VIEW_MODE_KEY, mode);
  };

  const handleGraphKind = (nextKind: GraphKind) => {
    setGraphKind(nextKind);
    setSelectedNodeId(null);
    window.localStorage.setItem(GRAPH_KIND_KEY, nextKind);
  };

  const handleToolChange = (tool: string) => {
    setSelectedTool(tool);
    setSelectedNodeId(null);
    window.localStorage.setItem(EXECUTION_TOOL_KEY, tool);
  };

  const handleModelChange = (nextModelId: string) => {
    setModelId(nextModelId);
    setSelectedNodeId(null);
  };

  const handleNodeClick = (nodeId: string) => {
    setSelectedNodeId((current) => (current === nodeId ? null : nodeId));
  };

  const handleOpenQuery = (filePath: string) => {
    openFile(filePath);
    setActiveTab("sql");
  };

  const handleOpenExecutionStepSql = () => {
    const sqlPath = executionStepDetailQuery.data?.sql_model?.path;
    if (typeof sqlPath === "string" && sqlPath.trim()) {
      openFile(sqlPath);
      setActiveTab("sql");
      return;
    }
    addToast("SQL path is unavailable for this step", "info");
  };

  const handleNavigateWorkflowRef = (refName: string, refData: unknown) => {
    const refObj = (refData ?? {}) as Record<string, unknown>;
    const folder = typeof refObj.folder === "string" ? refObj.folder : null;
    const queryName = typeof refObj.query_name === "string" ? refObj.query_name : null;
    const fullRef = typeof refObj.full_ref === "string" ? refObj.full_ref : refName;
    const parts = fullRef.replace(/^_w\./, "").split(".").filter(Boolean);
    const fallbackFolder = parts.length >= 2 ? parts[0] : null;
    const fallbackQuery = parts.length >= 2 ? parts[1] : null;

    const target = executionNodes.find((step) => {
      const stepFolder = step.folder ?? "";
      const stepName = step.name ?? "";
      const normalizedStepName = stepName.endsWith(".sql") ? stepName.slice(0, -4) : stepName;
      const expectedFolder = folder ?? fallbackFolder;
      const expectedQuery = queryName ?? fallbackQuery;
      return (
        (expectedFolder ? stepFolder === expectedFolder : true) &&
        (expectedQuery ? normalizedStepName === expectedQuery || stepName === expectedQuery : false)
      );
    });

    if (target) {
      setSelectedNodeId(target.step_id);
      return;
    }
    addToast(`Workflow ref unresolved: ${refName}`, "info");
  };

  const handleNavigateModelRef = (refName: string) => {
    setActiveTab("model");
    addToast(`Opened Model Editor for ref ${refName}`, "info");
  };

  const handleExportPng = async () => {
    if (!graphExportRef.current || !currentProjectId || !modelId) return;
    try {
      const dataUrl = await toPng(graphExportRef.current, {
        cacheBust: true,
        pixelRatio: 2,
        backgroundColor: "#ffffff",
      });
      const link = document.createElement("a");
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      link.download = `lineage-${currentProjectId}-${modelId}-${stamp}.png`;
      link.href = dataUrl;
      link.click();
      addToast("Lineage exported", "success");
    } catch {
      addToast("Failed to export lineage PNG", "error");
    }
  };

  const clearFilters = () => {
    setSearchValue("");
    if (graphKind === "execution") {
      setSelectedTool("all_tools");
      window.localStorage.setItem(EXECUTION_TOOL_KEY, "all_tools");
    }
  };

  const renderGraphContent = () => {
    const graphQuery = graphKind === "lineage" ? lineageQuery : executionGraphQuery;

    if (graphQuery.isLoading) {
      return <LineageSkeleton />;
    }

    if (graphQuery.isError) {
      return (
        <ShellState
          icon="⚠"
          title={graphKind === "lineage" ? "Failed to load lineage" : "Failed to load execution graph"}
          description={graphQuery.error instanceof Error ? graphQuery.error.message : "Unknown error"}
          actions={
            <button className="lg-state-btn" onClick={() => graphQuery.refetch()} type="button">
              ↻ Retry
            </button>
          }
          danger
        />
      );
    }

    if (visibleNodes.length === 0) {
      return (
        <ShellState
          icon="⊘"
          title={graphKind === "lineage" ? "No folders match" : "No steps match"}
          description={
            <>
              {searchValue ? `Search "${searchValue}" returned no results.` : null}
              {searchValue && overlayHidden > 0 ? " " : null}
              {overlayHidden > 0
                ? `${graphKind === "execution" ? "Context/tool filters" : "Context filter"} hide ${overlayHidden} ${
                    graphKind === "lineage" ? "folder" : "step"
                  }${overlayHidden !== 1 ? "s" : ""}.`
                : null}
            </>
          }
          actions={
            <div className="lg-state-btns">
              {searchValue ? (
                <button className="lg-state-btn" onClick={() => setSearchValue("")} type="button">
                  Clear search
                </button>
              ) : null}
              {contextHidden > 0 ? (
                <button className="lg-state-btn" onClick={() => setActiveTab("project")} type="button">
                  Change context
                </button>
              ) : null}
            </div>
          }
        />
      );
    }

    return (
      <div ref={graphExportRef} className="lg-graph-surface">
        <DagGraph
          ref={dagGraphRef}
          nodes={visibleNodes}
          edges={visibleEdges}
          selectedNodeId={selectedNodeId}
          onNodeSelect={handleNodeClick}
          layoutDirection={viewMode === "vertical" ? "TB" : "LR"}
          compact={viewMode === "compact"}
          source={effectiveSource}
        />
      </div>
    );
  };

  return (
    <section className="workbench lg-root">
      {!currentProjectId ? (
        <ShellState
          icon="⊡"
          title="No project selected"
          description="Select a project to explore its model lineage graph."
          actions={
            <button className="lg-state-btn" onClick={() => setActiveTab("project")} type="button">
              Go to Projects
            </button>
          }
        />
      ) : treeQuery.isLoading ? (
        <LoadingShell />
      ) : treeQuery.isError ? (
        <ShellState
          icon="⚠"
          title="Failed to load project"
          description={treeQuery.error instanceof Error ? treeQuery.error.message : "Unknown error"}
          actions={
            <button className="lg-state-btn" onClick={() => treeQuery.refetch()} type="button">
              ↻ Retry
            </button>
          }
          danger
        />
      ) : modelIds.length === 0 ? (
        <ShellState
          icon="◼"
          title="No models found"
          description={
            <>
              No model directories were found in <span className="lg-code-pill">model/</span>. Add a model to see its
              lineage.
            </>
          }
          actions={
            <button className="lg-state-btn" onClick={() => setActiveTab("project")} type="button">
              Open Project Info
            </button>
          }
        />
      ) : (
        <>
          <LineageHeader
            graphKind={graphKind}
            modelName={modelId || null}
            contextMode={multiMode ? "multi" : "single"}
            activeContext={activeContext}
            activeContexts={activeContexts}
            workflowSource={effectiveSource}
            visibleCount={visibleIds.size}
            totalCount={allNodes.length}
            isFiltered={isFiltered}
          />

          <LineageToolbar
            models={modelIds}
            selectedModel={modelId}
            onModelChange={handleModelChange}
            graphKind={graphKind}
            onGraphKindChange={handleGraphKind}
            toolOptions={executionToolOptions}
            selectedTool={selectedTool}
            onToolChange={handleToolChange}
            viewMode={viewMode}
            onViewMode={handleViewMode}
            search={searchValue}
            onSearch={setSearchValue}
            onExport={handleExportPng}
          />

          <FallbackBanner
            graphKind={graphKind}
            source={effectiveSource}
            status={effectiveWorkflowStatus}
            isRebuilding={rebuildMutation.isPending}
            onRebuild={() => rebuildMutation.mutate()}
          />

          <WorkflowDiagnosticsPanel
            modelId={modelId}
            status={(modelDiagnosticsQuery.data?.status ?? effectiveWorkflowStatus) as
              | "ready"
              | "stale"
              | "building"
              | "error"
              | "missing"
              | null}
            source={(modelDiagnosticsQuery.data?.source ?? effectiveSource) as "framework_cli" | "fallback" | null}
            diagnostics={modelDiagnosticsQuery.data?.diagnostics}
            updatedAt={modelDiagnosticsQuery.data?.updated_at}
          />

          <FilterNote
            graphKind={graphKind}
            searchTerm={searchValue}
            searchHidden={searchHidden}
            overlayHidden={overlayHidden}
            overlayLabel={graphKind === "execution" ? "context/tool filters" : "context"}
            visibleCount={visibleIds.size}
            onClearSearch={() => setSearchValue("")}
            onClearAll={clearFilters}
          />

          <LineageSummary
            graphKind={graphKind}
            folders={allNodes.length}
            queries={graphKind === "lineage" ? lineageQuery.data?.summary.queries ?? 0 : executionGraphQuery.data?.summary.scopes.sql ?? 0}
            params={graphKind === "lineage" ? lineageQuery.data?.summary.params ?? 0 : executionGraphQuery.data?.summary.scopes.params ?? 0}
            ctes={graphKind === "lineage" ? countNodeCtes(allNodes) : 0}
            isFiltered={isFiltered}
            source={effectiveSource}
            visibleFolders={visibleIds.size}
          />

          <div className="lg-body">
            <GraphArea
              showLegend
              onFitView={() => dagGraphRef.current?.fitView()}
              onReset={() => dagGraphRef.current?.resetView()}
              onZoomIn={() => dagGraphRef.current?.zoomIn()}
              onZoomOut={() => dagGraphRef.current?.zoomOut()}
            >
              {renderGraphContent()}
            </GraphArea>

            {graphKind === "lineage" ? (
              <DetailPanel
                selectedNode={selectedNode as LineageNode | null}
                onOpenQuery={handleOpenQuery}
                inboundCount={connectionCounts.inbound}
                outboundCount={connectionCounts.outbound}
                modelId={modelId}
                formatPath={formatNodePath}
              />
            ) : (
              <ExecutionDetailPanel
                selectedStep={selectedExecutionStep as WorkflowExecutionStep | null}
                selectedStepDetail={executionStepDetailQuery.data}
                isDetailLoading={executionStepDetailQuery.isLoading}
                inboundCount={connectionCounts.inbound}
                outboundCount={connectionCounts.outbound}
                onOpenStepSql={handleOpenExecutionStepSql}
                onNavigateWorkflowRef={handleNavigateWorkflowRef}
                onNavigateModelRef={handleNavigateModelRef}
              />
            )}
          </div>
        </>
      )}
    </section>
  );
}
