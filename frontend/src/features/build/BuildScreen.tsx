import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Editor, { DiffEditor } from "@monaco-editor/react";

import {
  fetchBuildFileContent,
  fetchBuildFiles,
  fetchBuildHistory,
  fetchProjectContexts,
  fetchProjectTree,
  getBuildDownloadUrl,
  getBuildFileDownloadUrl,
  type BuildFilesTreeNode,
  type BuildRunResult,
  type FileNode,
} from "../../api/projects";
import { useTheme } from "../../app/providers/ThemeProvider";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";

type BuildEngine = "dqcr" | "airflow" | "dbt" | "oracle_plsql";

const ENGINE_OPTIONS: Array<{ id: BuildEngine; label: string }> = [
  { id: "dqcr", label: "DQCR" },
  { id: "airflow", label: "Airflow" },
  { id: "dbt", label: "dbt" },
  { id: "oracle_plsql", label: "Oracle PL/SQL" },
];

function findModelIds(tree: FileNode): string[] {
  const rootChildren = tree.children ?? [];
  const modelRoot = rootChildren.find(
    (child) => child.type === "directory" && ["model", "models"].includes(child.name.toLowerCase()),
  );
  if (!modelRoot || !modelRoot.children) return [];
  return modelRoot.children.filter((child) => child.type === "directory").map((child) => child.name);
}

function findFirstFilePath(node: BuildFilesTreeNode | null): string | null {
  if (!node) return null;
  if (node.type === "file") return node.path;
  for (const child of node.children ?? []) {
    const resolved = findFirstFilePath(child);
    if (resolved) return resolved;
  }
  return null;
}

function OutputTreeNode({
  node,
  selectedPath,
  onSelect,
}: {
  node: BuildFilesTreeNode;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  if (node.type === "file") {
    const isSelected = selectedPath === node.path;
    return (
      <li>
        <button
          type="button"
          className={isSelected ? "build-tree-file-btn build-tree-file-btn-active" : "build-tree-file-btn"}
          onClick={() => onSelect(node.path)}
        >
          <span className="build-tree-file">{node.name}</span>
          <span className="build-tree-meta">{node.size_bytes ?? 0} B</span>
        </button>
      </li>
    );
  }

  return (
    <li>
      <span className="build-tree-dir">{node.path ? node.name : "output"}</span>
      {(node.children ?? []).length > 0 ? (
        <ul className="build-tree-list">
          {(node.children ?? []).map((child) => (
            <OutputTreeNode key={child.path || child.name} node={child} selectedPath={selectedPath} onSelect={onSelect} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export default function BuildScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const addToast = useUiStore((state) => state.addToast);
  const queryClient = useQueryClient();
  const { theme } = useTheme();
  const [engine, setEngine] = useState<BuildEngine>("dqcr");
  const [context, setContext] = useState("default");
  const [modelId, setModelId] = useState<string>("");
  const [dryRun, setDryRun] = useState(false);
  const [outputPath, setOutputPath] = useState("");
  const [selectedBuildId, setSelectedBuildId] = useState<string | null>(null);
  const [selectedOutputFilePath, setSelectedOutputFilePath] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState<number | null>(null);
  const [buildStage, setBuildStage] = useState<string | null>(null);

  const treeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const contextsQuery = useQuery({
    queryKey: ["contexts", currentProjectId],
    queryFn: () => fetchProjectContexts(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const buildHistoryQuery = useQuery({
    queryKey: ["buildHistory", currentProjectId],
    queryFn: () => fetchBuildHistory(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const buildFilesQuery = useQuery({
    queryKey: ["buildFiles", currentProjectId, selectedBuildId],
    queryFn: () => fetchBuildFiles(currentProjectId as string, selectedBuildId as string),
    enabled: Boolean(currentProjectId && selectedBuildId),
  });

  const buildFileContentQuery = useQuery({
    queryKey: ["buildFileContent", currentProjectId, selectedBuildId, selectedOutputFilePath],
    queryFn: () => fetchBuildFileContent(currentProjectId as string, selectedBuildId as string, selectedOutputFilePath as string),
    enabled: Boolean(currentProjectId && selectedBuildId && selectedOutputFilePath),
  });

  const previousBuildId = useMemo(() => {
    const history = buildHistoryQuery.data ?? [];
    if (!selectedBuildId) return null;
    const index = history.findIndex((item) => item.build_id === selectedBuildId);
    if (index < 0 || index + 1 >= history.length) return null;
    return history[index + 1]?.build_id ?? null;
  }, [buildHistoryQuery.data, selectedBuildId]);

  const previousBuildFilesQuery = useQuery({
    queryKey: ["buildFiles", currentProjectId, previousBuildId],
    queryFn: () => fetchBuildFiles(currentProjectId as string, previousBuildId as string),
    enabled: Boolean(currentProjectId && previousBuildId),
  });

  const previousBuildFileContentQuery = useQuery({
    queryKey: ["buildFileContent", currentProjectId, previousBuildId, selectedOutputFilePath],
    queryFn: () => fetchBuildFileContent(currentProjectId as string, previousBuildId as string, selectedOutputFilePath as string),
    enabled: Boolean(currentProjectId && previousBuildId && selectedOutputFilePath),
    retry: false,
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

  useEffect(() => {
    const contexts = contextsQuery.data ?? [];
    if (!contexts.length) return;
    if (!contexts.some((item) => item.id === context)) {
      setContext(contexts[0].id);
    }
  }, [contextsQuery.data, context]);

  useEffect(() => {
    const firstBuild = buildHistoryQuery.data?.[0];
    if (!firstBuild) {
      setSelectedBuildId(null);
      return;
    }
    if (!selectedBuildId || !buildHistoryQuery.data?.some((item) => item.build_id === selectedBuildId)) {
      setSelectedBuildId(firstBuild.build_id);
    }
  }, [buildHistoryQuery.data, selectedBuildId]);

  useEffect(() => {
    const firstFilePath = findFirstFilePath(buildFilesQuery.data?.tree ?? null);
    if (!firstFilePath) {
      setSelectedOutputFilePath(null);
      return;
    }
    if (!selectedOutputFilePath) {
      setSelectedOutputFilePath(firstFilePath);
      return;
    }
    const existsInCurrentBuild = (buildFilesQuery.data?.files ?? []).some((file) => file.path === selectedOutputFilePath);
    if (!existsInCurrentBuild) {
      setSelectedOutputFilePath(firstFilePath);
    }
  }, [buildFilesQuery.data, selectedOutputFilePath]);

  const runBuildViaWs = () => {
    if (!currentProjectId || !modelId || isBuilding) return;
    setIsBuilding(true);
    setBuildProgress(0);
    setBuildStage("connecting");

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/build/${currentProjectId}`);
    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          model_id: modelId,
          engine,
          context,
          dry_run: dryRun,
          output_path: outputPath.trim() || undefined,
        }),
      );
    };

    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data) as
        | { type: "progress"; percent: number; stage: string }
        | { type: "done"; result: BuildRunResult }
        | { type: "error"; message: string };

      if (data.type === "progress") {
        setBuildProgress(data.percent);
        setBuildStage(data.stage);
        return;
      }
      if (data.type === "error") {
        setIsBuilding(false);
        setBuildProgress(null);
        setBuildStage(null);
        addToast(data.message || "Build failed", "error");
        ws.close();
        return;
      }
      setBuildProgress(100);
      setBuildStage("completed");
      setIsBuilding(false);
      await queryClient.invalidateQueries({ queryKey: ["buildHistory", currentProjectId] });
      setSelectedBuildId(data.result.build_id);
      addToast(`Build ${data.result.build_id} completed`, "success");
      ws.close();
    };

    ws.onerror = () => {
      setIsBuilding(false);
      setBuildProgress(null);
      setBuildStage(null);
      addToast("Build websocket connection failed", "error");
      ws.close();
    };
  };

  const restoreBuildConfig = (item: BuildRunResult) => {
    setEngine(item.engine);
    setContext(item.context);
    setModelId(item.model);
    setDryRun(Boolean(item.dry_run));
    const output = item.output_path;
    setOutputPath(output.startsWith(".dqcr_builds/") ? "" : output);
    setSelectedBuildId(item.build_id);
    addToast(`Restored config from ${item.build_id}`, "success");
  };

  const diffSummary = useMemo(() => {
    const currentFiles = new Set((buildFilesQuery.data?.files ?? []).map((item) => item.path));
    const previousFiles = new Set((previousBuildFilesQuery.data?.files ?? []).map((item) => item.path));
    const added = Array.from(currentFiles).filter((item) => !previousFiles.has(item));
    const removed = Array.from(previousFiles).filter((item) => !currentFiles.has(item));
    const shared = Array.from(currentFiles).filter((item) => previousFiles.has(item));
    return { added, removed, shared };
  }, [buildFilesQuery.data?.files, previousBuildFilesQuery.data?.files]);

  if (!currentProjectId) {
    return (
      <section className="workbench">
        <h1>Build</h1>
        <p>Select a project to run build.</p>
      </section>
    );
  }

  return (
    <section className="workbench">
      <h1>Build</h1>
      <div className="build-config">
        <div className="build-config-grid">
          <label>
            Engine
            <select value={engine} onChange={(event) => setEngine(event.target.value as BuildEngine)}>
              {ENGINE_OPTIONS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Context
            <select value={context} onChange={(event) => setContext(event.target.value)}>
              {(contextsQuery.data ?? [{ id: "default", name: "default" }]).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Model
            <select value={modelId} onChange={(event) => setModelId(event.target.value)}>
              {modelIds.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="build-config-checkbox">
            <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
            Dry run
          </label>
          <label>
            Output path (optional)
            <input
              className="ui-input"
              value={outputPath}
              onChange={(event) => setOutputPath(event.target.value)}
              placeholder=".dqcr_builds/custom"
            />
          </label>
        </div>
        <button className="action-btn action-btn-primary" type="button" onClick={runBuildViaWs} disabled={isBuilding || !modelId}>
          {isBuilding ? "Building..." : "Run Build"}
        </button>
      </div>

      {buildProgress !== null ? (
        <p className="build-progress">
          Progress: {buildProgress}% {buildStage ? `(${buildStage})` : ""}
        </p>
      ) : null}

      <div className="build-layout">
        <section className="build-card">
          <h2>Build History</h2>
          <ul className="build-history-list">
            {(buildHistoryQuery.data ?? []).map((item) => (
              <li key={item.build_id}>
                <button
                  type="button"
                  className={selectedBuildId === item.build_id ? "build-history-item build-history-item-active" : "build-history-item"}
                  onClick={() => setSelectedBuildId(item.build_id)}
                >
                  <strong>{item.build_id}</strong>
                  <span>{item.engine}</span>
                  <span>{new Date(item.timestamp).toLocaleString()}</span>
                </button>
                <button type="button" className="action-btn build-restore-btn" onClick={() => restoreBuildConfig(item)}>
                  Restore
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="build-card">
          <h2>Output Files</h2>
          {buildFilesQuery.data?.tree ? (
            <div className="build-output-layout">
              <div>
                <ul className="build-tree-list">
                  <OutputTreeNode
                    node={buildFilesQuery.data.tree}
                    selectedPath={selectedOutputFilePath}
                    onSelect={setSelectedOutputFilePath}
                  />
                </ul>
                {selectedBuildId ? (
                  <a className="action-btn build-download-link" href={getBuildDownloadUrl(currentProjectId, selectedBuildId)}>
                    Download ZIP
                  </a>
                ) : null}
                {selectedBuildId && selectedOutputFilePath ? (
                  <a
                    className="action-btn build-download-link"
                    href={getBuildFileDownloadUrl(currentProjectId, selectedBuildId, selectedOutputFilePath)}
                  >
                    Download File
                  </a>
                ) : null}
              </div>
              <div className="build-viewer">
                <p className="build-viewer-head">
                  {selectedOutputFilePath ?? "Select file"}
                </p>
                <Editor
                  height="320px"
                  defaultLanguage="sql"
                  value={buildFileContentQuery.data ?? ""}
                  theme={theme === "dark" ? "vs-dark" : "light"}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 12,
                    wordWrap: "on",
                    lineNumbers: "on",
                  }}
                />
              </div>
            </div>
          ) : (
            <p className="build-empty">No output files yet.</p>
          )}
        </section>
      </div>

      <section className="build-card build-diff-card">
        <h2>Diff with previous build</h2>
        {!previousBuildId ? <p className="build-empty">No previous build to compare.</p> : null}
        {previousBuildId ? (
          <>
            <p className="build-diff-meta">
              Current: <code>{selectedBuildId}</code> vs Previous: <code>{previousBuildId}</code>
            </p>
            <p className="build-diff-meta">
              Added: {diffSummary.added.length}, Removed: {diffSummary.removed.length}, Shared: {diffSummary.shared.length}
            </p>
            {selectedOutputFilePath ? (
              <DiffEditor
                height="280px"
                original={previousBuildFileContentQuery.data ?? ""}
                modified={buildFileContentQuery.data ?? ""}
                language="sql"
                theme={theme === "dark" ? "vs-dark" : "light"}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 12,
                  renderSideBySide: true,
                  wordWrap: "on",
                }}
              />
            ) : (
              <p className="build-empty">Select a file from output tree to see diff.</p>
            )}
          </>
        ) : null}
      </section>
    </section>
  );
}
