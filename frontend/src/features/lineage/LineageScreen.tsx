import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import "reactflow/dist/style.css";

import {
  fetchModelLineage,
  fetchProjectTree,
  fetchProjectWorkflowStatus,
  rebuildModelWorkflow,
  FileNode,
  LineageNode,
} from "../../api/projects";
import { useContextStore } from "../../app/store/contextStore";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import DagGraph, { DagGraphHandle } from "./DagGraph";
import "./lineage.css";
import { DetailPanel } from "./components/DetailPanel";
import { FallbackBanner } from "./components/FallbackBanner";
import { FilterNote } from "./components/FilterNote";
import { GraphArea } from "./components/GraphArea";
import { LineageHeader } from "./components/LineageHeader";
import { LineageSummary } from "./components/LineageSummary";
import { LineageToolbar } from "./components/LineageToolbar";
import { computeVisibleNodes, countNodeCtes, formatNodePath, getConnectionCounts, nodeMatchesSearch } from "./lineageUtils";

type LineageViewMode = "horizontal" | "vertical" | "compact";

const VIEW_MODE_KEY = "dqcr_lineage_viewmode";

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
  const [viewMode, setViewMode] = useState<LineageViewMode>(() => {
    const stored = window.localStorage.getItem(VIEW_MODE_KEY);
    return stored === "vertical" || stored === "compact" || stored === "horizontal" ? stored : "horizontal";
  });
  const [searchValue, setSearchValue] = useState("");

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
    enabled: Boolean(currentProjectId && modelId),
  });

  const rebuildMutation = useMutation({
    mutationFn: async () => {
      if (!currentProjectId) return;
      const models = workflowStatusQuery.data?.models ?? [];
      const targetModels = modelId
        ? models.filter((item) => item.model_id === modelId && (item.status === "stale" || item.status === "error"))
        : models.filter((item) => item.status === "stale" || item.status === "error");
      await Promise.all(targetModels.map((item) => rebuildModelWorkflow(currentProjectId, item.model_id)));
    },
    onSuccess: () => {
      addToast("Workflow rebuild started", "info");
      workflowStatusQuery.refetch();
    },
    onError: () => {
      addToast("Workflow rebuild failed", "error");
    },
  });

  const allNodes = lineageQuery.data?.nodes ?? [];
  const allEdges = lineageQuery.data?.edges ?? [];
  const selectedContexts = multiMode ? activeContexts : activeContext ? [activeContext] : [];

  const enabledContextsMap = useMemo(
    () =>
      Object.fromEntries(allNodes.map((node) => [node.id, node.enabled_contexts] as const)) as Record<string, string[] | null>,
    [allNodes],
  );

  const visibleIds = useMemo(
    () => computeVisibleNodes(allNodes, searchValue, selectedContexts, enabledContextsMap),
    [allNodes, searchValue, selectedContexts, enabledContextsMap],
  );

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

  const isFiltered = searchValue.trim().length > 0 || contextHidden > 0;

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

  const source = activeWorkflowModelState?.source ?? null;

  const handleViewMode = (mode: LineageViewMode) => {
    setViewMode(mode);
    window.localStorage.setItem(VIEW_MODE_KEY, mode);
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
  };

  const renderGraphContent = () => {
    if (lineageQuery.isLoading) {
      return <LineageSkeleton />;
    }

    if (lineageQuery.isError) {
      return (
        <ShellState
          icon="⚠"
          title="Failed to load lineage"
          description={lineageQuery.error instanceof Error ? lineageQuery.error.message : "Unknown error"}
          actions={
            <button className="lg-state-btn" onClick={() => lineageQuery.refetch()} type="button">
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
          title="No folders match"
          description={
            <>
              {searchValue ? `Search "${searchValue}" returned no results.` : null}
              {searchValue && contextHidden > 0 ? " " : null}
              {contextHidden > 0 ? `Context filter hides ${contextHidden} folder${contextHidden !== 1 ? "s" : ""}.` : null}
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
          source={source}
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
            modelName={modelId || null}
            contextMode={multiMode ? "multi" : "single"}
            activeContext={activeContext}
            activeContexts={activeContexts}
            workflowSource={source}
            visibleCount={visibleIds.size}
            totalCount={allNodes.length}
            isFiltered={isFiltered}
          />

          <LineageToolbar
            models={modelIds}
            selectedModel={modelId}
            onModelChange={handleModelChange}
            viewMode={viewMode}
            onViewMode={handleViewMode}
            search={searchValue}
            onSearch={setSearchValue}
            onExport={handleExportPng}
          />

          <FallbackBanner
            source={source}
            isRebuilding={rebuildMutation.isPending}
            onRebuild={() => rebuildMutation.mutate()}
          />

          <FilterNote
            searchTerm={searchValue}
            searchHidden={searchHidden}
            contextHidden={contextHidden}
            visibleCount={visibleIds.size}
            onClearSearch={() => setSearchValue("")}
            onClearAll={clearFilters}
          />

          <LineageSummary
            folders={allNodes.length}
            queries={lineageQuery.data?.summary.queries ?? 0}
            params={lineageQuery.data?.summary.params ?? 0}
            ctes={countNodeCtes(allNodes)}
            isFiltered={isFiltered}
            source={source}
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

            <DetailPanel
              selectedNode={selectedNode as LineageNode | null}
              onOpenQuery={handleOpenQuery}
              inboundCount={connectionCounts.inbound}
              outboundCount={connectionCounts.outbound}
              modelId={modelId}
              formatPath={formatNodePath}
            />
          </div>
        </>
      )}
    </section>
  );
}
