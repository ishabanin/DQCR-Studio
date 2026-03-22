export type ProjectStructureActionMode = "rename" | "delete" | "new-file" | "new-folder" | "new-model";

export interface ProjectStructureActionState {
  mode: ProjectStructureActionMode;
  path: string;
  nodeType: "file" | "directory";
}

const MODE_LABELS: Record<ProjectStructureActionMode, string> = {
  rename: "Переименовать",
  delete: "Удалить",
  "new-file": "Новый файл",
  "new-folder": "Новая папка",
  "new-model": "Новая модель",
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
      ? `Переименовать ${state.nodeType === "directory" ? "папку" : "файл"}`
      : state.mode === "delete"
        ? `Удалить ${state.nodeType === "directory" ? "папку" : "файл"}`
        : state.mode === "new-file"
          ? "Создать файл"
          : state.mode === "new-folder"
            ? "Создать папку"
            : "Создать модель";

  const fieldLabel = state.mode === "rename" ? "Новое имя" : state.mode === "new-model" ? "ID модели" : "Путь";
  const primaryLabel = pending ? "Выполняется..." : state.mode === "delete" ? "Удалить" : "Применить";

  return (
    <div className="sidebar-dialog-overlay" role="dialog" aria-modal="true">
      <div className="sidebar-dialog">
        <div className="sidebar-dialog-head">
          <h2>{title}</h2>
          <button type="button" className="action-btn" onClick={onCancel}>
            Закрыть
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
            Удалить <code>{state.path}</code>? Это действие удалит элемент из дерева проекта.
          </p>
        ) : (
          <>
            <p className="sidebar-dialog-copy">
              {state.mode === "rename"
                ? `Текущее имя: ${baseName}`
                : state.mode === "new-model"
                  ? `Корень моделей: ${getModelRootPath()}`
                  : `Базовый путь: ${normalizeRootPath(parentPath) || "корень проекта"}`}
            </p>
            <label className="sidebar-dialog-field">
              <span>{fieldLabel}</span>
              <input className="ui-input" value={value} onChange={(event) => onValueChange(event.target.value)} autoFocus />
            </label>
            {state.mode === "new-model" ? (
              <p className="sidebar-dialog-copy">
                Будет создан <code>{`${getModelRootPath()}/${value.trim() || "<ModelId>"}/model.yml`}</code> с пустым каркасом модели.
              </p>
            ) : null}
          </>
        )}
        <div className="sidebar-dialog-actions">
          <button type="button" className="action-btn" onClick={onCancel}>
            Отмена
          </button>
          <button type="button" className="action-btn action-btn-primary" onClick={onConfirm} disabled={pending}>
            {primaryLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
