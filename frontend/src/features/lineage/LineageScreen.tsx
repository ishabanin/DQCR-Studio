import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import "reactflow/dist/style.css";

import { fetchModelLineage, fetchProjectTree, FileNode } from "../../api/projects";
import { useContextStore } from "../../app/store/contextStore";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import DagGraph from "./DagGraph";

type LineageViewMode = "horizontal" | "vertical" | "compact";

function findModelIds(tree: FileNode): string[] {
  const rootChildren = tree.children ?? [];
  const modelRoot = rootChildren.find(
    (child) => child.type === "directory" && ["model", "models"].includes(child.name.toLowerCase()),
  );
  if (!modelRoot || !modelRoot.children) return [];
  return modelRoot.children.filter((child) => child.type === "directory").map((child) => child.name);
}

export default function LineageScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const activeContext = useContextStore((state) => state.activeContext);
  const activeContexts = useContextStore((state) => state.activeContexts);
  const multiMode = useContextStore((state) => state.multiMode);
  const openFile = useEditorStore((state) => state.openFile);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const addToast = useUiStore((state) => state.addToast);
  const [modelId, setModelId] = useState<string>("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<LineageViewMode>("horizontal");
  const [searchValue, setSearchValue] = useState("");
  const graphExportRef = useRef<HTMLDivElement | null>(null);

  const treeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
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
    if (!modelIds.includes(modelId)) {
      setModelId(modelIds[0]);
    }
  }, [modelIds, modelId]);

  const lineageQuery = useQuery({
    queryKey: ["lineage", currentProjectId, modelId],
    queryFn: () => fetchModelLineage(currentProjectId as string, modelId),
    enabled: Boolean(currentProjectId && modelId),
  });

  const visibleNodes = useMemo(() => {
    if (!lineageQuery.data?.nodes) return [];
    const query = searchValue.trim().toLowerCase();
    const contexts = multiMode ? activeContexts : [activeContext];
    return lineageQuery.data.nodes.filter((node) => {
      const byContext =
        node.enabled_contexts === null || node.enabled_contexts.some((ctx) => contexts.includes(ctx));
      if (!byContext) return false;
      if (!query) return true;
      return node.name.toLowerCase().includes(query);
    });
  }, [lineageQuery.data?.nodes, searchValue, multiMode, activeContexts, activeContext]);

  const visibleEdges = useMemo(() => {
    if (!lineageQuery.data?.edges) return [];
    const nodeIds = new Set(visibleNodes.map((node) => node.id));
    return lineageQuery.data.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  }, [lineageQuery.data?.edges, visibleNodes]);

  useEffect(() => {
    if (!visibleNodes.length) {
      setSelectedNodeId(null);
      return;
    }
    const exists = visibleNodes.some((node) => node.id === selectedNodeId);
    if (!exists) {
      setSelectedNodeId(visibleNodes[0].id);
    }
  }, [visibleNodes, selectedNodeId]);

  if (!currentProjectId) {
    return (
      <section className="workbench">
        <h1>Lineage</h1>
        <p>Select a project to load lineage.</p>
      </section>
    );
  }

  if (treeQuery.isLoading) {
    return (
      <section className="workbench">
        <h1>Lineage</h1>
        <p>Loading project structure...</p>
      </section>
    );
  }

  if (treeQuery.isError) {
    return (
      <section className="workbench">
        <h1>Lineage</h1>
        <p>Failed to load project files.</p>
      </section>
    );
  }

  if (!modelIds.length) {
    return (
      <section className="workbench">
        <h1>Lineage</h1>
        <p>No models found in project.</p>
      </section>
    );
  }

  const handleExportPng = async () => {
    if (!graphExportRef.current) return;
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

  return (
    <section className="workbench">
      <h1>Lineage</h1>
      <div className="lineage-toolbar">
        <label htmlFor="lineage-model-select">Model</label>
        <select id="lineage-model-select" value={modelId} onChange={(event) => setModelId(event.target.value)}>
          {modelIds.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <div className="lineage-mode-switch">
          <button
            className={viewMode === "horizontal" ? "lineage-mode-btn lineage-mode-btn-active" : "lineage-mode-btn"}
            onClick={() => setViewMode("horizontal")}
            type="button"
          >
            Horizontal
          </button>
          <button
            className={viewMode === "vertical" ? "lineage-mode-btn lineage-mode-btn-active" : "lineage-mode-btn"}
            onClick={() => setViewMode("vertical")}
            type="button"
          >
            Vertical
          </button>
          <button
            className={viewMode === "compact" ? "lineage-mode-btn lineage-mode-btn-active" : "lineage-mode-btn"}
            onClick={() => setViewMode("compact")}
            type="button"
          >
            Compact
          </button>
        </div>
        <input
          className="lineage-search-input"
          placeholder="Search folders..."
          value={searchValue}
          onChange={(event) => setSearchValue(event.target.value)}
        />
        <button className="lineage-export-btn" onClick={handleExportPng} type="button">
          Export PNG
        </button>
      </div>

      {lineageQuery.isLoading ? <p>Loading lineage graph...</p> : null}
      {lineageQuery.isError ? <p>Failed to load lineage data.</p> : null}

      {lineageQuery.data ? (
        <>
          <div className="lineage-summary">
            <span className="lineage-badge">{lineageQuery.data.summary.folders} folders</span>
            <span className="lineage-badge">{lineageQuery.data.summary.queries} queries</span>
            <span className="lineage-badge">{lineageQuery.data.summary.params} params</span>
          </div>
          <div className="lineage-main">
            <div ref={graphExportRef}>
              <DagGraph
                nodes={visibleNodes}
                edges={visibleEdges}
                selectedNodeId={selectedNodeId}
                onNodeSelect={setSelectedNodeId}
                layoutDirection={viewMode === "vertical" ? "TB" : "LR"}
                compact={viewMode === "compact"}
              />
            </div>
            {selectedNodeId ? (
              <aside className="lineage-detail-panel">
                {(() => {
                  const selectedNode = visibleNodes.find((node) => node.id === selectedNodeId);
                  if (!selectedNode) return null;
                  return (
                    <>
                      <h2>{selectedNode.name}</h2>
                      <div className="lineage-detail-section">
                        <span className="lineage-detail-label">Materialization</span>
                        <span className="lineage-materialized">{selectedNode.materialized}</span>
                      </div>
                      <div className="lineage-detail-section">
                        <span className="lineage-detail-label">Parameters</span>
                        {selectedNode.parameters.length > 0 ? (
                          <div className="lineage-chip-list">
                            {selectedNode.parameters.map((param) => (
                              <span key={param} className="lineage-sql-chip">
                                {param}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p>None</p>
                        )}
                      </div>
                      <div className="lineage-detail-section">
                        <span className="lineage-detail-label">CTE</span>
                        {selectedNode.ctes.length > 0 ? (
                          <div className="lineage-chip-list">
                            {selectedNode.ctes.map((cte) => (
                              <span key={cte} className="lineage-sql-chip">
                                {cte}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p>None</p>
                        )}
                      </div>
                      <div className="lineage-detail-section">
                        <span className="lineage-detail-label">Queries</span>
                        <div className="lineage-query-actions">
                          {selectedNode.queries.map((queryName) => {
                            const filePath = `${selectedNode.path}/${queryName}`;
                            return (
                              <button
                                key={queryName}
                                className="lineage-open-query-btn"
                                onClick={() => {
                                  openFile(filePath);
                                  setActiveTab("sql");
                                }}
                                type="button"
                              >
                                Open {queryName}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </>
                  );
                })()}
              </aside>
            ) : null}
          </div>
          {visibleNodes.length === 0 ? <p>No folders match current context/filter.</p> : null}
        </>
      ) : null}
    </section>
  );
}
