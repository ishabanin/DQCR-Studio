export type ProjectStructureActionMode = "rename" | "delete" | "new-file" | "new-folder" | "new-model";

export interface ProjectStructureActionState {
  mode: ProjectStructureActionMode;
  path: string;
  nodeType: "file" | "directory";
}

const MODE_LABELS: Record<ProjectStructureActionMode, string> = {
  rename: "Rename",
  delete: "Delete",
  "new-file": "New file",
  "new-folder": "New folder",
  "new-model": "New model",
};

function normalizeRootPath(path: string): string {
  return path === "." ? "" : path;
}

function getModelRootPath(): string {
  return "model";
}

export default function ProjectStructureDialog({
  state,
  value,
  availableModes,
  onValueChange,
  onModeChange,
  onCancel,
  onConfirm,
  pending,
}: {
  state: ProjectStructureActionState | null;
  value: string;
  availableModes: ProjectStructureActionMode[];
  onValueChange: (value: string) => void;
  onModeChange: (mode: ProjectStructureActionMode) => void;
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
          : state.mode === "new-folder"
            ? "Create folder"
            : "Create model";

  const fieldLabel = state.mode === "rename" ? "New name" : state.mode === "new-model" ? "Model ID" : "Path";
  const primaryLabel = pending ? "Working..." : state.mode === "delete" ? "Delete" : "Apply";

  return (
    <div className="sidebar-dialog-overlay" role="dialog" aria-modal="true">
      <div className="sidebar-dialog">
        <div className="sidebar-dialog-head">
          <h2>{title}</h2>
          <button type="button" className="action-btn" onClick={onCancel}>
            Close
          </button>
        </div>
        {availableModes.length > 1 ? (
          <div className="sidebar-dialog-mode-list">
            {availableModes.map((mode) => (
              <button
                key={mode}
                type="button"
                className={mode === state.mode ? "sidebar-dialog-mode sidebar-dialog-mode-active" : "sidebar-dialog-mode"}
                onClick={() => onModeChange(mode)}
              >
                {MODE_LABELS[mode]}
              </button>
            ))}
          </div>
        ) : null}
        {state.mode === "delete" ? (
          <p className="sidebar-dialog-copy">
            Delete <code>{state.path}</code>? This action removes the item from the project tree.
          </p>
        ) : (
          <>
            <p className="sidebar-dialog-copy">
              {state.mode === "rename"
                ? `Current name: ${baseName}`
                : state.mode === "new-model"
                  ? `Model root: ${getModelRootPath()}`
                  : `Base path: ${normalizeRootPath(parentPath) || "project root"}`}
            </p>
            <label className="sidebar-dialog-field">
              <span>{fieldLabel}</span>
              <input className="ui-input" value={value} onChange={(event) => onValueChange(event.target.value)} autoFocus />
            </label>
            {state.mode === "new-model" ? (
              <p className="sidebar-dialog-copy">
                Creates <code>{`${getModelRootPath()}/${value.trim() || "<ModelId>"}/model.yml`}</code> with an empty model scaffold.
              </p>
            ) : null}
          </>
        )}
        <div className="sidebar-dialog-actions">
          <button type="button" className="action-btn" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={onConfirm} disabled={pending}>
            {primaryLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
