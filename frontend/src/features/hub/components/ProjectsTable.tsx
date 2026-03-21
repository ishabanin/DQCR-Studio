import type { ProjectListItem, SortDir, SortKey } from "../types";
import { CACHE_LABELS, formatRelativeDate, getProjectPalette } from "../utils";

const TABLE_COLUMNS = [
  { key: "icon", label: "", width: 40, sortable: false },
  { key: "name", label: "Project", width: null, sortable: true },
  { key: "visibility", label: "Visibility", width: 80, sortable: false },
  { key: "type", label: "Type", width: 80, sortable: false },
  { key: "tags", label: "Tags", width: 140, sortable: false },
  { key: "models", label: "Models", width: 60, sortable: true },
  { key: "sql_count", label: "SQL files", width: 70, sortable: true },
  { key: "cache", label: "Cache", width: 100, sortable: false },
  { key: "modified", label: "Modified", width: 110, sortable: true },
  { key: "actions", label: "", width: 60, sortable: false },
] as const;

interface ProjectsTableProps {
  projects: ProjectListItem[];
  sortBy: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  onOpen: (projectId: string) => void;
  onEdit: (projectId: string) => void;
  onDelete: (projectId: string) => void;
}

function toSortKey(key: (typeof TABLE_COLUMNS)[number]["key"]): SortKey | null {
  if (key === "name") return "name";
  if (key === "modified") return "modified_at";
  if (key === "models") return "model_count";
  if (key === "sql_count") return "sql_count";
  return null;
}

export function ProjectsTable({ projects, sortBy, sortDir, onSort, onOpen, onEdit, onDelete }: ProjectsTableProps) {
  return (
    <div style={{ border: "var(--hub-border-subtle)", borderRadius: "var(--hub-radius-card)", overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", tableLayout: "fixed" }}>
        <thead>
          <tr>
            {TABLE_COLUMNS.map((col) => {
              const columnSortKey = toSortKey(col.key);
              return (
                <th
                  key={col.key}
                  style={{
                    width: col.width ?? undefined,
                    padding: "6px 12px",
                    fontSize: "var(--hub-text-2xs)",
                    fontWeight: "var(--hub-weight-medium)",
                    color: "var(--color-text-tertiary)",
                    textAlign: "left",
                    background: "var(--hub-surface-panel)",
                    borderBottom: "var(--hub-border-subtle)",
                    whiteSpace: "nowrap",
                    cursor: col.sortable ? "pointer" : "default",
                    userSelect: "none",
                  }}
                  onClick={columnSortKey ? () => onSort(columnSortKey) : undefined}
                >
                  {col.label}
                  {columnSortKey && sortBy === columnSortKey && <span style={{ marginLeft: 4, fontSize: 10 }}>{sortDir === "asc" ? "▲" : "▼"}</span>}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => {
            const palette = getProjectPalette(project.project_id);
            return (
              <tr key={project.project_id} className="hub-table-row" onClick={() => onOpen(project.project_id)}>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "var(--hub-radius-md)",
                      background: palette.bg,
                      color: palette.color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 12,
                      fontWeight: "var(--hub-weight-medium)",
                    }}
                  >
                    {project.name.charAt(0).toUpperCase()}
                  </div>
                </td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <div style={{ fontWeight: "var(--hub-weight-medium)", fontSize: "var(--hub-text-base)", color: "var(--color-text-primary)" }}>{project.name}</div>
                  <div
                    style={{
                      fontSize: "var(--hub-text-xs)",
                      color: "var(--color-text-secondary)",
                      marginTop: 2,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: 320,
                    }}
                  >
                    {project.description}
                  </div>
                </td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <span className={`hub-badge hub-badge-${project.visibility}`}>{project.visibility === "public" ? "◎" : "◉"}</span>
                </td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <span className={`hub-badge hub-badge-${project.project_type}`}>{project.project_type}</span>
                </td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <div style={{ display: "flex", gap: 3, flexWrap: "nowrap", overflow: "hidden" }}>
                    {project.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className="hub-badge hub-badge-tag">
                        {tag}
                      </span>
                    ))}
                    {project.tags.length > 2 && (
                      <span className="hub-badge" style={{ background: "var(--hub-surface-panel)", color: "var(--color-text-tertiary)" }}>
                        +{project.tags.length - 2}
                      </span>
                    )}
                  </div>
                </td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)", fontSize: "var(--hub-text-sm)" }}>{project.model_count}</td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)", fontSize: "var(--hub-text-sm)" }}>{project.sql_count}</td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div className={`hub-cache-dot hub-cache-${project.cache_status}`} />
                    <span style={{ fontSize: "var(--hub-text-xs)", color: "var(--color-text-secondary)" }}>{CACHE_LABELS[project.cache_status]}</span>
                  </div>
                </td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)", fontSize: "var(--hub-text-xs)" }}>{formatRelativeDate(project.modified_at)}</td>
                <td style={{ padding: "var(--hub-cell-py) var(--hub-cell-px)" }}>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button
                      className="hub-btn-secondary"
                      style={{ padding: "2px 6px", fontSize: 11 }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onEdit(project.project_id);
                      }}
                    >
                      ⚙
                    </button>
                    <button
                      className="hub-btn-secondary"
                      style={{ padding: "2px 6px", fontSize: 11 }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onDelete(project.project_id);
                      }}
                    >
                      ✕
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
