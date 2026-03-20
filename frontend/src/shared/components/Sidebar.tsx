import { type ReactNode, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProjectFolder, deleteProjectPath, fetchProjectTree, fetchProjects, FileNode, renameProjectPath, saveFileContent } from "../../api/projects";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import Tooltip from "./ui/Tooltip";

type SidebarActionMode = "rename" | "delete" | "new-file" | "new-folder";

interface SidebarActionState {
  mode: SidebarActionMode;
  path: string;
  nodeType: "file" | "directory";
}

type ActionIconName = "new-file" | "new-folder" | "rename" | "delete";
type NodeVisualKind =
  | "project"
  | "readme"
  | "contexts"
  | "context-file"
  | "parameters"
  | "parameter-file"
  | "model"
  | "model-object"
  | "model-file"
  | "folder-config"
  | "sql-folder"
  | "sql-file"
  | "yaml-file"
  | "folder"
  | "file";

function normalizeRootPath(path: string): string {
  return path === "." ? "" : path;
}

function joinPath(basePath: string, name: string): string {
  const base = normalizeRootPath(basePath).replace(/\/+$/g, "");
  const next = name.trim().replace(/^\/+/g, "");
  if (!base) return next;
  if (!next) return base;
  return `${base}/${next}`;
}

function getAncestorPaths(path: string): string[] {
  const normalized = normalizeRootPath(path);
  if (!normalized) return [];
  const parts = normalized.split("/");
  return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join("/"));
}

function shouldAutoExpand(node: FileNode): boolean {
  if (node.path === ".") return true;
  return ["contexts", "parameters", "model"].includes(node.path.toLowerCase());
}

function inferNodeKind(node: FileNode, parentPath: string | null): NodeVisualKind {
  const lowerName = node.name.toLowerCase();
  const lowerPath = normalizeRootPath(node.path).toLowerCase();
  const lowerParent = parentPath?.toLowerCase() ?? "";

  if (node.type === "directory") {
    if (lowerPath === "." || lowerName === "sample") return "project";
    if (lowerName === "contexts") return "contexts";
    if (lowerName === "parameters") return "parameters";
    if (lowerName === "model") return "model";
    if (lowerName === "sql") return "sql-folder";
    if (lowerParent === "model") return "model-object";
    return "folder";
  }

  if (lowerName === "project.yml") return "project";
  if (lowerName === "readme.md") return "readme";
  if (lowerName === "model.yml") return "model-file";
  if (lowerName === "folder.yml") return "folder-config";
  if (lowerPath.startsWith("contexts/")) return "context-file";
  if (lowerPath.startsWith("parameters/") || lowerParent.endsWith("/parameters") || lowerParent === "parameters") return "parameter-file";
  if (lowerName.endsWith(".sql")) return "sql-file";
  if (lowerName.endsWith(".yml") || lowerName.endsWith(".yaml")) return "yaml-file";
  return "file";
}

function IconBase({
  children,
  tone,
  className = "",
}: {
  children: ReactNode;
  tone: string;
  className?: string;
}) {
  return (
    <span className={`node-glyph ${tone} ${className}`.trim()} aria-hidden="true">
      {children}
    </span>
  );
}

function NodeIcon({ kind }: { kind: NodeVisualKind }) {
  switch (kind) {
    case "project":
      return <IconBase tone="node-glyph-project">P</IconBase>;
    case "readme":
      return <IconBase tone="node-glyph-readme">R</IconBase>;
    case "contexts":
      return <IconBase tone="node-glyph-contexts">C</IconBase>;
    case "context-file":
      return <IconBase tone="node-glyph-context">C</IconBase>;
    case "parameters":
      return <IconBase tone="node-glyph-parameters">PRM</IconBase>;
    case "parameter-file":
      return <IconBase tone="node-glyph-parameter">PRM</IconBase>;
    case "model":
      return <IconBase tone="node-glyph-model">M</IconBase>;
    case "model-object":
      return <IconBase tone="node-glyph-model-object">OBJ</IconBase>;
    case "model-file":
      return <IconBase tone="node-glyph-model-file">CFG</IconBase>;
    case "folder-config":
      return <IconBase tone="node-glyph-folder-config">FLD</IconBase>;
    case "sql-folder":
      return <IconBase tone="node-glyph-sql-folder">SQL</IconBase>;
    case "sql-file":
      return <IconBase tone="node-glyph-sql-file">SQL</IconBase>;
    case "yaml-file":
      return <IconBase tone="node-glyph-yaml-file">YML</IconBase>;
    default:
      return <IconBase tone="node-glyph-folder">{kind === "folder" ? "DIR" : "FILE"}</IconBase>;
  }
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg className={expanded ? "tree-chevron tree-chevron-expanded" : "tree-chevron"} viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ActionGlyph({ name }: { name: ActionIconName }) {
  if (name === "new-file") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M5 2.75h4.5L13 6.25v6.5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="M9.5 2.75v3.5H13" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="M8 7.2v4.1M5.95 9.25h4.1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  if (name === "new-folder") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M2.5 4.5a1 1 0 0 1 1-1h2.3l1.2 1.2H12.5a1 1 0 0 1 1 1v5.8a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1V4.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="M8 6.7v3.6M6.2 8.5h3.6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  if (name === "rename") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 11.8 3.6 9l5.8-5.8 2.8 2.8-5.8 5.8L3 11.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="m8.6 4 2.8 2.8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M4.5 5.5h7M6 5.5v6M10 5.5v6M3.5 4h9l-.7 8.3a1 1 0 0 1-1 .9H5.2a1 1 0 0 1-1-.9L3.5 4ZM6 2.8h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TreeActionButton({
  icon,
  label,
  onClick,
}: {
  icon: ActionIconName;
  label: string;
  onClick: () => void;
}) {
  return (
    <Tooltip text={label}>
      <button
        type="button"
        className="tree-action-btn"
        aria-label={label}
        onClick={(event) => {
          event.stopPropagation();
          onClick();
        }}
      >
        <ActionGlyph name={icon} />
      </button>
    </Tooltip>
  );
}

function SidebarTreeNode({
  node,
  depth,
  activeFilePath,
  expandedPaths,
  onToggle,
  onOpen,
  onAction,
  parentPath = null,
}: {
  node: FileNode;
  depth: number;
  activeFilePath: string | null;
  expandedPaths: Record<string, boolean>;
  onToggle: (path: string) => void;
  onOpen: (path: string) => void;
  onAction: (mode: SidebarActionMode, path: string, nodeType: "file" | "directory") => void;
  parentPath?: string | null;
}) {
  const kind = inferNodeKind(node, parentPath);
  const isDirectory = node.type === "directory";
  const isActive = node.path === activeFilePath;
  const hasChildren = Boolean(node.children && node.children.length > 0);
  const expanded = isDirectory ? expandedPaths[node.path] ?? shouldAutoExpand(node) : false;
  const style = { paddingLeft: `${12 + depth * 14}px` };
  const rowClassName = [
    "tree-row",
    isDirectory ? "tree-row-directory" : "tree-row-file",
    isActive ? "tree-row-active" : "",
    kind === "project" ? "tree-row-project" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <li>
      <div
        className={rowClassName}
        style={style}
        onContextMenu={(event) => {
          event.preventDefault();
          onAction(isDirectory ? "new-file" : "rename", node.path, node.type);
        }}
      >
        <button
          type="button"
          className={isDirectory ? "tree-main-hit tree-main-hit-directory" : "tree-main-hit"}
          onClick={() => {
            if (isDirectory) {
              onToggle(node.path);
              return;
            }
            onOpen(node.path);
          }}
        >
          {isDirectory ? (
            <span className="tree-expander" aria-hidden="true">
              {hasChildren ? <ChevronIcon expanded={expanded} /> : <span className="tree-expander-spacer" />}
            </span>
          ) : (
            <span className="tree-expander tree-expander-spacer" aria-hidden="true" />
          )}
          <NodeIcon kind={kind} />
          <span className="tree-label">{node.path === "." ? "SampleDQCR" : node.name}</span>
        </button>
        <div className="tree-row-actions">
          {isDirectory ? (
            <>
              <TreeActionButton icon="new-file" label="New file" onClick={() => onAction("new-file", node.path, "directory")} />
              <TreeActionButton icon="new-folder" label="New folder" onClick={() => onAction("new-folder", node.path, "directory")} />
              {node.path !== "." ? <TreeActionButton icon="rename" label="Rename" onClick={() => onAction("rename", node.path, "directory")} /> : null}
              {node.path !== "." ? <TreeActionButton icon="delete" label="Delete" onClick={() => onAction("delete", node.path, "directory")} /> : null}
            </>
          ) : (
            <>
              <TreeActionButton icon="rename" label="Rename" onClick={() => onAction("rename", node.path, "file")} />
              <TreeActionButton icon="delete" label="Delete" onClick={() => onAction("delete", node.path, "file")} />
            </>
          )}
        </div>
      </div>
      {isDirectory && expanded && hasChildren ? (
        <ul className="tree-list">
          {node.children?.map((child) => (
            <SidebarTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              activeFilePath={activeFilePath}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
              onOpen={onOpen}
              onAction={onAction}
              parentPath={node.path}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function SidebarActionDialog({
  state,
  value,
  onValueChange,
  onModeChange,
  onCancel,
  onConfirm,
  pending,
}: {
  state: SidebarActionState | null;
  value: string;
  onValueChange: (value: string) => void;
  onModeChange: (mode: SidebarActionMode) => void;
  onCancel: () => void;
  onConfirm: () => void;
  pending: boolean;
}) {
  if (!state) return null;

  const baseName = state.path.split("/").pop() ?? state.path;
  const parentPath = state.nodeType === "directory" ? state.path : state.path.split("/").slice(0, -1).join("/");
  const title =
    state.mode === "rename"
      ? `Rename ${state.nodeType}`
      : state.mode === "delete"
        ? `Delete ${state.nodeType}`
        : state.mode === "new-file"
          ? "Create file"
          : "Create folder";

  return (
    <div className="sidebar-dialog-overlay" role="dialog" aria-modal="true">
      <div className="sidebar-dialog">
        <div className="sidebar-dialog-head">
          <h2>{title}</h2>
          <button type="button" className="action-btn" onClick={onCancel}>
            Close
          </button>
        </div>
        <div className="sidebar-dialog-mode-list">
          {(["rename", "new-file", "new-folder", "delete"] as SidebarActionMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={mode === state.mode ? "sidebar-dialog-mode sidebar-dialog-mode-active" : "sidebar-dialog-mode"}
              onClick={() => onModeChange(mode)}
            >
              {mode}
            </button>
          ))}
        </div>
        {state.mode === "delete" ? (
          <p className="sidebar-dialog-copy">
            Delete <code>{state.path}</code>? This action removes the item from the project tree.
          </p>
        ) : (
          <>
            <p className="sidebar-dialog-copy">
              {state.mode === "rename"
                ? `Current name: ${baseName}`
                : `Base path: ${normalizeRootPath(parentPath) || "project root"}`}
            </p>
            <label className="sidebar-dialog-field">
              <span>{state.mode === "rename" ? "New name" : "Path"}</span>
              <input className="ui-input" value={value} onChange={(event) => onValueChange(event.target.value)} autoFocus />
            </label>
          </>
        )}
        <div className="sidebar-dialog-actions">
          <button type="button" className="action-btn" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={onConfirm} disabled={pending}>
            {pending ? "Working..." : state.mode === "delete" ? "Delete" : "Apply"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const queryClient = useQueryClient();
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const setProject = useProjectStore((state) => state.setProject);
  const sidebarCollapsed = useUiStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);
  const addToast = useUiStore((state) => state.addToast);
  const openFile = useEditorStore((state) => state.openFile);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const activeFilePath = useEditorStore((state) => state.activeFilePath);
  const [actionState, setActionState] = useState<SidebarActionState | null>(null);
  const [actionValue, setActionValue] = useState("");
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({ ".": true });

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  useEffect(() => {
    if (!currentProjectId && projectsQuery.data && projectsQuery.data.length > 0) {
      const preferred = projectsQuery.data.find((project) => project.id === "sample") ?? projectsQuery.data[0];
      setProject(preferred.id);
    }
  }, [currentProjectId, projectsQuery.data, setProject]);

  const treeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  useEffect(() => {
    if (!treeQuery.data) return;

    setExpandedPaths((previous) => {
      const next: Record<string, boolean> = { ...previous, ".": true };

      const walk = (node: FileNode) => {
        if (node.type === "directory" && shouldAutoExpand(node) && next[node.path] === undefined) {
          next[node.path] = true;
        }
        node.children?.forEach(walk);
      };

      walk(treeQuery.data);

      if (activeFilePath) {
        for (const path of getAncestorPaths(activeFilePath)) {
          next[path] = true;
        }
      }

      return next;
    });
  }, [treeQuery.data, activeFilePath]);

  const refreshTree = async () => {
    await queryClient.invalidateQueries({ queryKey: ["projectTree", currentProjectId] });
  };

  const renameMutation = useMutation({
    mutationFn: ({ path, newName }: { path: string; newName: string }) => renameProjectPath(currentProjectId as string, path, newName),
    onSuccess: async () => {
      await refreshTree();
      addToast("Path renamed", "success");
      setActionState(null);
    },
    onError: () => addToast("Failed to rename path", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ path }: { path: string }) => deleteProjectPath(currentProjectId as string, path),
    onSuccess: async () => {
      await refreshTree();
      addToast("Path deleted", "success");
      setActionState(null);
    },
    onError: () => addToast("Failed to delete path", "error"),
  });

  const createFileMutation = useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) => saveFileContent(currentProjectId as string, path, content),
    onSuccess: async (_, variables) => {
      await refreshTree();
      openFile(variables.path);
      setActiveTab("sql");
      addToast("File created", "success");
      setActionState(null);
    },
    onError: () => addToast("Failed to create file", "error"),
  });

  const createFolderMutation = useMutation({
    mutationFn: ({ path }: { path: string }) => createProjectFolder(currentProjectId as string, path),
    onSuccess: async (_, variables) => {
      setExpandedPaths((previous) => ({ ...previous, [variables.path]: true }));
      await refreshTree();
      addToast("Folder created", "success");
      setActionState(null);
    },
    onError: () => addToast("Failed to create folder", "error"),
  });

  const pending = renameMutation.isPending || deleteMutation.isPending || createFileMutation.isPending || createFolderMutation.isPending;

  const openActionDialog = (mode: SidebarActionMode, path: string, nodeType: "file" | "directory") => {
    const currentName = path.split("/").pop() ?? "";
    const basePath = nodeType === "directory" ? path : path.split("/").slice(0, -1).join("/");
    const nextValue =
      mode === "rename"
        ? currentName
        : mode === "new-file"
          ? joinPath(basePath, "new_file.sql")
          : mode === "new-folder"
            ? joinPath(basePath, "new_folder")
            : "";

    setActionState({ mode, path, nodeType });
    setActionValue(nextValue);
  };

  const switchActionMode = (mode: SidebarActionMode) => {
    if (!actionState) return;
    openActionDialog(mode, actionState.path, actionState.nodeType);
  };

  const submitAction = () => {
    if (!actionState || !currentProjectId) return;

    if (actionState.mode === "delete") {
      deleteMutation.mutate({ path: actionState.path });
      return;
    }

    const trimmed = actionValue.trim().replace(/^\/+/g, "");
    if (!trimmed) {
      addToast("Value is required", "error");
      return;
    }

    if (actionState.mode === "rename") {
      renameMutation.mutate({ path: actionState.path, newName: trimmed });
      return;
    }

    if (actionState.mode === "new-folder") {
      createFolderMutation.mutate({ path: trimmed });
      return;
    }

    const content = trimmed.endsWith(".sql") ? "-- New SQL file\nSELECT 1;\n" : "";
    createFileMutation.mutate({ path: trimmed, content });
  };

  const togglePath = (path: string) => {
    setExpandedPaths((previous) => ({ ...previous, [path]: !(previous[path] ?? shouldAutoExpand({ name: "", path, type: "directory" })) }));
  };

  const projectName = useMemo(() => projectsQuery.data?.find((project) => project.id === currentProjectId)?.name ?? "Project Explorer", [currentProjectId, projectsQuery.data]);

  return (
    <>
      <aside className={sidebarCollapsed ? "sidebar sidebar-collapsed" : "sidebar"}>
        <div className="sidebar-head">
          <div className="sidebar-head-title">
            <span className="sidebar-head-eyebrow">Project Explorer</span>
            {!sidebarCollapsed ? <strong>{projectName}</strong> : null}
          </div>
          <div className="sidebar-head-actions">
            {!sidebarCollapsed ? (
              <>
                <TreeActionButton icon="new-file" label="New file" onClick={() => openActionDialog("new-file", ".", "directory")} />
                <TreeActionButton icon="new-folder" label="New folder" onClick={() => openActionDialog("new-folder", ".", "directory")} />
              </>
            ) : null}
            <Tooltip text={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}>
              <button type="button" className="tree-action-btn tree-action-btn-head" onClick={toggleSidebar} aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}>
                <ChevronIcon expanded={!sidebarCollapsed} />
              </button>
            </Tooltip>
          </div>
        </div>
        {!sidebarCollapsed && treeQuery.data ? (
          <div className="sidebar-body">
            <ul className="tree-list tree-root-list">
              <SidebarTreeNode
                node={treeQuery.data}
                depth={0}
                activeFilePath={activeFilePath}
                expandedPaths={expandedPaths}
                onToggle={togglePath}
                onOpen={(path) => {
                  openFile(path);
                  setActiveTab("sql");
                }}
                onAction={openActionDialog}
              />
            </ul>
          </div>
        ) : null}
      </aside>

      <SidebarActionDialog
        state={actionState}
        value={actionValue}
        onValueChange={setActionValue}
        onModeChange={switchActionMode}
        onCancel={() => setActionState(null)}
        onConfirm={submitAction}
        pending={pending}
      />
    </>
  );
}
