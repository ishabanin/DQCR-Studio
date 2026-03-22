import { type MouseEvent as ReactMouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProjectFolder, createProjectModel, deleteProjectPath, fetchProjectTree, fetchProjects, FileNode, renameProjectPath, saveFileContent } from "../../api/projects";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import ProjectStructureDialog, { type ProjectStructureActionMode, type ProjectStructureActionState } from "./ProjectStructureDialog";
import Tooltip from "./ui/Tooltip";

type ActionIconName = "new-file" | "new-folder" | "new-model" | "rename" | "delete" | "collapse-all" | "reveal-active" | "system-folders";
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

function isSystemDirectory(node: FileNode): boolean {
  return node.type === "directory" && node.path !== "." && node.name.startsWith(".");
}

function filterTreeForDisplay(node: FileNode, showSystemFolders: boolean): FileNode | null {
  if (!showSystemFolders && isSystemDirectory(node)) {
    return null;
  }

  if (node.type !== "directory") {
    return node;
  }

  const filteredChildren = (node.children ?? [])
    .map((child) => filterTreeForDisplay(child, showSystemFolders))
    .filter((child): child is FileNode => Boolean(child));

  return { ...node, children: filteredChildren };
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

function getLineageTargetFromPath(path: string): { modelId: string; nodePath: string | null } | null {
  const normalized = normalizeRootPath(path);
  if (!normalized) return null;

  const parts = normalized.split("/").filter(Boolean);
  if (parts.length < 2) return null;
  if (!["model", "models"].includes(parts[0].toLowerCase())) return null;

  const modelId = parts[1];
  if (!modelId) return null;

  if (parts.length === 2) {
    return { modelId, nodePath: null };
  }

  const workflowLikeRoot = parts[2]?.toLowerCase();
  if (workflowLikeRoot === "workflow" || workflowLikeRoot === "sql") {
    const folderName = parts[3];
    return {
      modelId,
      nodePath: folderName ? normalized : null,
    };
  }

  return { modelId, nodePath: normalized };
}

function splitNormalizedPath(path: string): string[] {
  return normalizeRootPath(path)
    .split("/")
    .filter(Boolean);
}

function getModelIdFromPath(path: string): string | null {
  const parts = splitNormalizedPath(path);
  if (parts.length < 2) return null;
  if (!["model", "models"].includes(parts[0].toLowerCase())) return null;
  return parts[1] ?? null;
}

function isModelRootDirectory(path: string): boolean {
  const parts = splitNormalizedPath(path);
  return parts.length === 2 && ["model", "models"].includes(parts[0].toLowerCase());
}

function canCreateModelAtPath(path: string, nodeType: "file" | "directory"): boolean {
  if (nodeType !== "directory") return false;
  const normalized = normalizeRootPath(path).toLowerCase();
  return normalized === "" || normalized === "model";
}

function getAvailableActionModes(path: string, nodeType: "file" | "directory"): ProjectStructureActionMode[] {
  if (nodeType === "file") {
    return ["rename", "delete"];
  }

  const modes: ProjectStructureActionMode[] = ["new-file", "new-folder"];
  if (canCreateModelAtPath(path, nodeType)) {
    modes.push("new-model");
  }
  if (path !== ".") {
    modes.push("rename", "delete");
  }
  return modes;
}

function getParameterScopeFilterFromPath(path: string): string | null {
  const parts = splitNormalizedPath(path);
  if (parts.length === 1 && parts[0].toLowerCase() === "parameters") {
    return "global";
  }
  if (parts.length >= 3 && ["model", "models"].includes(parts[0].toLowerCase()) && parts[2].toLowerCase() === "parameters") {
    const modelId = parts[1];
    return modelId ? `model:${modelId}` : null;
  }
  return null;
}

function NodeIcon({ kind }: { kind: NodeVisualKind }) {
  switch (kind) {
    case "project":
      return (
        <span className="node-glyph node-glyph-project" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M3 4.2a1.2 1.2 0 0 1 1.2-1.2h7.6A1.2 1.2 0 0 1 13 4.2v7.6a1.2 1.2 0 0 1-1.2 1.2H4.2A1.2 1.2 0 0 1 3 11.8V4.2Z" stroke="currentColor" strokeWidth="1.2" />
            <path d="M5.2 6h5.6M5.2 8h5.6M5.2 10h3.2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
        </span>
      );
    case "readme":
      return (
        <span className="node-glyph node-glyph-readme" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M4.2 2.8h5l2.6 2.6v7a.8.8 0 0 1-.8.8H4.2a.8.8 0 0 1-.8-.8V3.6a.8.8 0 0 1 .8-.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M9.2 2.8v2.6h2.6M5.5 7h4.8M5.5 9h4.8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      );
    case "contexts":
      return (
        <span className="node-glyph node-glyph-contexts" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="4.8" stroke="currentColor" strokeWidth="1.2" />
            <path d="M3.8 8h8.4M8 3.2c1.2 1.3 1.9 3 1.9 4.8S9.2 11.5 8 12.8C6.8 11.5 6.1 9.8 6.1 8S6.8 4.5 8 3.2Z" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
          </svg>
        </span>
      );
    case "context-file":
      return (
        <span className="node-glyph node-glyph-context" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M4.4 3.4h4.2l2.4 2.4v6.2a.8.8 0 0 1-.8.8H4.4a.8.8 0 0 1-.8-.8V4.2a.8.8 0 0 1 .8-.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M7.2 6.2a2.2 2.2 0 1 0 0 4.4 2.2 2.2 0 0 0 0-4.4Z" stroke="currentColor" strokeWidth="1.1" />
          </svg>
        </span>
      );
    case "parameters":
      return (
        <span className="node-glyph node-glyph-parameters" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M4 4h8M4 8h8M4 12h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            <circle cx="6" cy="4" r="1.4" fill="currentColor" />
            <circle cx="10" cy="8" r="1.4" fill="currentColor" />
            <circle cx="7.5" cy="12" r="1.4" fill="currentColor" />
          </svg>
        </span>
      );
    case "parameter-file":
      return (
        <span className="node-glyph node-glyph-parameter" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M4.4 3.4h4.2l2.4 2.4v6.2a.8.8 0 0 1-.8.8H4.4a.8.8 0 0 1-.8-.8V4.2a.8.8 0 0 1 .8-.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M5.6 10.8 9.9 6.5M7.2 5.9h3.3v3.3" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      );
    case "model":
      return (
        <span className="node-glyph node-glyph-model" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M8 2.8 12.2 5v6L8 13.2 3.8 11V5L8 2.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M3.8 5 8 7.2 12.2 5M8 7.2V13" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
          </svg>
        </span>
      );
    case "model-object":
      return (
        <span className="node-glyph node-glyph-model-object" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <rect x="3.4" y="3.4" width="9.2" height="9.2" rx="1.6" stroke="currentColor" strokeWidth="1.2" />
            <path d="M5.7 5.8h4.6M5.7 8h4.6M5.7 10.2h2.8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
        </span>
      );
    case "model-file":
      return (
        <span className="node-glyph node-glyph-model-file" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M4.3 3.3h4.4l2.5 2.5v6a.9.9 0 0 1-.9.9H4.3a.9.9 0 0 1-.9-.9V4.2a.9.9 0 0 1 .9-.9Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M8 7.1a1.8 1.8 0 1 0 0 3.6 1.8 1.8 0 0 0 0-3.6Z" stroke="currentColor" strokeWidth="1.1" />
          </svg>
        </span>
      );
    case "folder-config":
      return (
        <span className="node-glyph node-glyph-folder-config" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M3 4.8a1 1 0 0 1 1-1h2.1l1 1H12a1 1 0 0 1 1 1v5.2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M6.2 8h3.6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
        </span>
      );
    case "sql-folder":
      return (
        <span className="node-glyph node-glyph-sql-folder" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M3 4.8a1 1 0 0 1 1-1h2.1l1 1H12a1 1 0 0 1 1 1v5.2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M5.5 8.2h5M5.5 10h3.7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
        </span>
      );
    case "sql-file":
      return (
        <span className="node-glyph node-glyph-sql-file" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <ellipse cx="8" cy="4.8" rx="3.2" ry="1.8" stroke="currentColor" strokeWidth="1.2" />
            <path d="M4.8 4.8v4.6c0 1 1.4 1.8 3.2 1.8s3.2-.8 3.2-1.8V4.8M5.8 9.4c.5.4 1.3.7 2.2.7.9 0 1.7-.3 2.2-.7" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      );
    case "yaml-file":
      return (
        <span className="node-glyph node-glyph-yaml-file" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            <path d="M4.4 3.4h4.2l2.4 2.4v6.2a.8.8 0 0 1-.8.8H4.4a.8.8 0 0 1-.8-.8V4.2a.8.8 0 0 1 .8-.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M5.6 6.5h4.8M5.6 8.5h4.8M5.6 10.5h3.3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
        </span>
      );
    default:
      return (
        <span className={`node-glyph ${kind === "folder" ? "node-glyph-folder" : "node-glyph-file"}`} aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none">
            {kind === "folder" ? (
              <path d="M3 4.8a1 1 0 0 1 1-1h2.1l1 1H12a1 1 0 0 1 1 1v5.2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            ) : (
              <>
                <path d="M4.4 3.4h4.2l2.4 2.4v6.2a.8.8 0 0 1-.8.8H4.4a.8.8 0 0 1-.8-.8V4.2a.8.8 0 0 1 .8-.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                <path d="M9.2 3.4v2.4h2.4" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
              </>
            )}
          </svg>
        </span>
      );
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

  if (name === "new-model") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M8 2.8 12.2 5v6L8 13.2 3.8 11V5L8 2.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="M3.8 5 8 7.2 12.2 5M8 7.2V13M12.8 3.7v3.2M11.2 5.3h3.2" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
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

  if (name === "collapse-all") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 4.5h10M3 8h10M3 11.5h10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        <path d="m10.8 3.3-1.8 1.2 1.8 1.2M10.8 6.8 9 8l1.8 1.2M10.8 10.3 9 11.5l1.8 1.2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (name === "reveal-active") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M2.5 8s2-3 5.5-3 5.5 3 5.5 3-2 3-5.5 3-5.5-3-5.5-3Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <circle cx="8" cy="8" r="1.8" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    );
  }

  if (name === "system-folders") {
    return (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M2.6 4.8a1 1 0 0 1 1-1h2.2l1.1 1.1h5.5a1 1 0 0 1 1 1v5.1a1 1 0 0 1-1 1h-8.8a1 1 0 0 1-1-1V4.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <circle cx="11.8" cy="10.7" r="2.1" stroke="currentColor" strokeWidth="1.1" />
        <path d="M10.6 10.7h2.4" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
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
  rootLabel,
  registerRowRef,
  parentPath = null,
}: {
  node: FileNode;
  depth: number;
  activeFilePath: string | null;
  expandedPaths: Record<string, boolean>;
  onToggle: (path: string) => void;
  onOpen: (path: string, nodeType: "file" | "directory") => void;
  onAction: (mode: ProjectStructureActionMode, path: string, nodeType: "file" | "directory") => void;
  rootLabel: string;
  registerRowRef: (path: string, element: HTMLLIElement | null) => void;
  parentPath?: string | null;
}) {
  const kind = inferNodeKind(node, parentPath);
  const isDirectory = node.type === "directory";
  const isActive = node.path === activeFilePath;
  const hasChildren = Boolean(node.children && node.children.length > 0);
  const expanded = isDirectory ? expandedPaths[node.path] ?? shouldAutoExpand(node) : false;
  const lineageTarget = getLineageTargetFromPath(node.path);
  const parameterScopeFilter = getParameterScopeFilterFromPath(node.path);
  const shouldOpenOnDirectoryClick = Boolean(lineageTarget || parameterScopeFilter || isModelRootDirectory(node.path));
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
    <li
      ref={(element) => {
        registerRowRef(node.path, element);
      }}
    >
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
              if (node.path === ".") {
                onOpen(node.path, node.type);
                return;
              }
              onToggle(node.path);
              if (shouldOpenOnDirectoryClick) {
                onOpen(node.path, node.type);
              }
              return;
            }
            onOpen(node.path, node.type);
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
          <span className="tree-label">{node.path === "." ? rootLabel : node.name}</span>
        </button>
        <div className="tree-row-actions">
          {isDirectory ? (
            <>
              <TreeActionButton icon="new-file" label="Новый файл" onClick={() => onAction("new-file", node.path, "directory")} />
              <TreeActionButton icon="new-folder" label="Новая папка" onClick={() => onAction("new-folder", node.path, "directory")} />
              {canCreateModelAtPath(node.path, node.type) ? (
                <TreeActionButton icon="new-model" label="Новая модель" onClick={() => onAction("new-model", node.path, "directory")} />
              ) : null}
              {node.path !== "." ? <TreeActionButton icon="rename" label="Переименовать" onClick={() => onAction("rename", node.path, "directory")} /> : null}
              {node.path !== "." ? <TreeActionButton icon="delete" label="Удалить" onClick={() => onAction("delete", node.path, "directory")} /> : null}
            </>
          ) : (
            <>
              <TreeActionButton icon="rename" label="Переименовать" onClick={() => onAction("rename", node.path, "file")} />
              <TreeActionButton icon="delete" label="Удалить" onClick={() => onAction("delete", node.path, "file")} />
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
              rootLabel={rootLabel}
              registerRowRef={registerRowRef}
              parentPath={node.path}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export default function Sidebar() {
  const queryClient = useQueryClient();
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const setProject = useProjectStore((state) => state.setProject);
  const sidebarCollapsed = useUiStore((state) => state.sidebarCollapsed);
  const sidebarWidth = useUiStore((state) => state.sidebarWidth);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);
  const setSidebarWidth = useUiStore((state) => state.setSidebarWidth);
  const setInitialModelId = useUiStore((state) => state.setInitialModelId);
  const setInitialParamScopeFilter = useUiStore((state) => state.setInitialParamScopeFilter);
  const addToast = useUiStore((state) => state.addToast);
  const openFile = useEditorStore((state) => state.openFile);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const activeFilePath = useEditorStore((state) => state.activeFilePath);
  const setLineageTarget = useEditorStore((state) => state.setLineageTarget);
  const [actionState, setActionState] = useState<ProjectStructureActionState | null>(null);
  const [actionValue, setActionValue] = useState("");
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({ ".": true });
  const [showSystemFolders, setShowSystemFolders] = useState(false);
  const rowRefs = useRef<Record<string, HTMLLIElement | null>>({});
  const resizeStateRef = useRef<{ startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    return () => {
      resizeStateRef.current = null;
    };
  }, []);

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
      addToast("Путь переименован", "success");
      setActionState(null);
    },
    onError: () => addToast("Не удалось переименовать путь", "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ path }: { path: string }) => deleteProjectPath(currentProjectId as string, path),
    onSuccess: async () => {
      await refreshTree();
      addToast("Путь удалён", "success");
      setActionState(null);
    },
    onError: () => addToast("Не удалось удалить путь", "error"),
  });

  const createFileMutation = useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) => saveFileContent(currentProjectId as string, path, content),
    onSuccess: async (_, variables) => {
      await refreshTree();
      openFile(variables.path);
      setActiveTab("sql");
      addToast("Файл создан", "success");
      setActionState(null);
    },
    onError: () => addToast("Не удалось создать файл", "error"),
  });

  const createFolderMutation = useMutation({
    mutationFn: ({ path }: { path: string }) => createProjectFolder(currentProjectId as string, path),
    onSuccess: async (_, variables) => {
      setExpandedPaths((previous) => ({ ...previous, [variables.path]: true }));
      await refreshTree();
      addToast("Папка создана", "success");
      setActionState(null);
    },
    onError: () => addToast("Не удалось создать папку", "error"),
  });

  const createModelMutation = useMutation({
    mutationFn: ({ modelId }: { modelId: string }) => createProjectModel(currentProjectId as string, modelId),
    onSuccess: async (payload) => {
      setExpandedPaths((previous) => ({
        ...previous,
        model: true,
        [payload.path]: true,
      }));
      await Promise.all([
        refreshTree(),
        queryClient.invalidateQueries({ queryKey: ["project-info", "tree", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["project-info", "workflow", currentProjectId] }),
      ]);
      setInitialModelId(payload.model_id);
      setActiveTab("model");
      addToast("Модель создана", "success");
      setActionState(null);
    },
    onError: () => addToast("Не удалось создать модель", "error"),
  });

  const pending =
    renameMutation.isPending || deleteMutation.isPending || createFileMutation.isPending || createFolderMutation.isPending || createModelMutation.isPending;

  const openActionDialog = (mode: ProjectStructureActionMode, path: string, nodeType: "file" | "directory") => {
    const currentName = path.split("/").pop() ?? "";
    const basePath = nodeType === "directory" ? path : path.split("/").slice(0, -1).join("/");
    const nextValue =
      mode === "rename"
        ? currentName
        : mode === "new-file"
          ? joinPath(basePath, "new_file.sql")
          : mode === "new-folder"
            ? joinPath(basePath, "new_folder")
            : mode === "new-model"
              ? "NewModel"
            : "";

    setActionState({ mode, path, nodeType });
    setActionValue(nextValue);
  };

  const switchActionMode = (mode: ProjectStructureActionMode) => {
    if (!actionState) return;
    openActionDialog(mode, actionState.path, actionState.nodeType);
  };

  const submitAction = () => {
    if (!actionState || !currentProjectId) return;

    if (actionState.mode === "delete") {
      deleteMutation.mutate({ path: actionState.path });
      return;
    }

    const trimmed = actionState.mode === "new-model" ? actionValue.trim() : actionValue.trim().replace(/^\/+/g, "");
    if (!trimmed) {
      addToast("Требуется значение", "error");
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

    if (actionState.mode === "new-model") {
      createModelMutation.mutate({ modelId: trimmed });
      return;
    }

    const content = trimmed.endsWith(".sql") ? "-- Новый SQL-файл\nSELECT 1;\n" : "";
    createFileMutation.mutate({ path: trimmed, content });
  };

  const togglePath = (path: string) => {
    setExpandedPaths((previous) => ({ ...previous, [path]: !(previous[path] ?? shouldAutoExpand({ name: "", path, type: "directory" })) }));
  };

  const collapseAll = () => {
    setExpandedPaths({ ".": true });
  };

  const revealActiveFile = () => {
    if (!activeFilePath) return;
    setExpandedPaths((previous) => {
      const next: Record<string, boolean> = { ...previous, ".": true };
      for (const path of getAncestorPaths(activeFilePath)) {
        next[path] = true;
      }
      return next;
    });

    window.requestAnimationFrame(() => {
      rowRefs.current[activeFilePath]?.scrollIntoView({ block: "nearest" });
    });
  };

  const startResize = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (sidebarCollapsed) return;

    resizeStateRef.current = {
      startX: event.clientX,
      startWidth: sidebarWidth,
    };

    const handlePointerMove = (moveEvent: MouseEvent) => {
      if (!resizeStateRef.current) return;
      const nextWidth = resizeStateRef.current.startWidth + (moveEvent.clientX - resizeStateRef.current.startX);
      setSidebarWidth(nextWidth);
    };

    const stopResize = () => {
      resizeStateRef.current = null;
      window.removeEventListener("mousemove", handlePointerMove);
      window.removeEventListener("mouseup", stopResize);
    };

    window.addEventListener("mousemove", handlePointerMove);
    window.addEventListener("mouseup", stopResize);
  };

  const projectName = useMemo(() => projectsQuery.data?.find((project) => project.id === currentProjectId)?.name ?? "Проводник проекта", [currentProjectId, projectsQuery.data]);
  const visibleTree = useMemo(() => {
    if (!treeQuery.data) return null;
    return filterTreeForDisplay(treeQuery.data, showSystemFolders);
  }, [treeQuery.data, showSystemFolders]);

  return (
    <>
      <aside className={sidebarCollapsed ? "sidebar sidebar-collapsed" : "sidebar"}>
        <div className="sidebar-head">
          <div className="sidebar-head-title">
            <span className="sidebar-head-eyebrow">Проводник проекта</span>
            {!sidebarCollapsed ? <strong>{projectName}</strong> : null}
          </div>
          <div className="sidebar-head-actions">
            {!sidebarCollapsed ? (
              <>
                <TreeActionButton icon="new-file" label="Новый файл" onClick={() => openActionDialog("new-file", ".", "directory")} />
                <TreeActionButton icon="new-folder" label="Новая папка" onClick={() => openActionDialog("new-folder", ".", "directory")} />
                <TreeActionButton icon="new-model" label="Новая модель" onClick={() => openActionDialog("new-model", ".", "directory")} />
                <TreeActionButton
                  icon="system-folders"
                  label={showSystemFolders ? "Скрыть системные папки" : "Показать системные папки"}
                  onClick={() => setShowSystemFolders((previous) => !previous)}
                />
                <TreeActionButton icon="collapse-all" label="Свернуть всё" onClick={collapseAll} />
                <TreeActionButton icon="reveal-active" label="Показать активный файл" onClick={revealActiveFile} />
              </>
            ) : null}
            <Tooltip text={sidebarCollapsed ? "Развернуть боковую панель" : "Свернуть боковую панель"}>
              <button type="button" className="tree-action-btn tree-action-btn-head" onClick={toggleSidebar} aria-label={sidebarCollapsed ? "Развернуть боковую панель" : "Свернуть боковую панель"}>
                <ChevronIcon expanded={!sidebarCollapsed} />
              </button>
            </Tooltip>
          </div>
        </div>
        {!sidebarCollapsed && treeQuery.data ? (
          <div className="sidebar-body">
            <ul className="tree-list tree-root-list">
              <SidebarTreeNode
                node={visibleTree ?? treeQuery.data}
                depth={0}
                activeFilePath={activeFilePath}
                expandedPaths={expandedPaths}
                onToggle={togglePath}
                onOpen={(path, nodeType) => {
                  if (path === ".") {
                    setActiveTab("project");
                    return;
                  }

                  if (nodeType === "file") {
                    openFile(path);
                    setActiveTab("sql");
                    return;
                  }

                  const parameterScopeFilter = getParameterScopeFilterFromPath(path);
                  if (parameterScopeFilter) {
                    setInitialParamScopeFilter(parameterScopeFilter);
                    setActiveTab("parameters");
                    return;
                  }

                  if (isModelRootDirectory(path)) {
                    const modelId = getModelIdFromPath(path);
                    if (modelId) {
                      setInitialModelId(modelId);
                    }
                    setActiveTab("model");
                    return;
                  }

                  const lineageTarget = getLineageTargetFromPath(path);
                  if (lineageTarget) {
                    setLineageTarget(lineageTarget);
                    setActiveTab("lineage");
                    return;
                  }

                  openFile(path);
                  setActiveTab("sql");
                }}
                onAction={openActionDialog}
                rootLabel={projectName}
                registerRowRef={(path, element) => {
                  rowRefs.current[path] = element;
                }}
              />
            </ul>
          </div>
        ) : null}
        {!sidebarCollapsed ? (
          <div
            className="sidebar-resize-handle"
            onMouseDown={startResize}
            role="separator"
            aria-orientation="vertical"
            aria-label="Изменить размер боковой панели"
          />
        ) : null}
      </aside>

      <ProjectStructureDialog
        state={actionState}
        value={actionValue}
        availableModes={actionState ? getAvailableActionModes(actionState.path, actionState.nodeType) : []}
        onValueChange={setActionValue}
        onModeChange={switchActionMode}
        onCancel={() => setActionState(null)}
        onConfirm={submitAction}
        pending={pending}
      />
    </>
  );
}
