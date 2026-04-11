import Badge from "../../../shared/components/ui/Badge";
import Button from "../../../shared/components/ui/Button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../shared/components/ui/Table";
import type { ProjectListItem, SortDir, SortKey } from "../types";
import { CACHE_LABELS, formatRelativeDate, getProjectPalette } from "../utils";

const TABLE_COLUMNS = [
  { key: "icon", label: "", widthClass: "hub-table-col-icon", sortable: false },
  { key: "name", label: "Project", widthClass: "", sortable: true },
  { key: "visibility", label: "Visibility", widthClass: "hub-table-col-sm", sortable: false },
  { key: "type", label: "Type", widthClass: "hub-table-col-sm", sortable: false },
  { key: "tags", label: "Tags", widthClass: "hub-table-col-tags", sortable: false },
  { key: "models", label: "Models", widthClass: "hub-table-col-xs", sortable: true },
  { key: "sql_count", label: "SQL files", widthClass: "hub-table-col-xs", sortable: true },
  { key: "cache", label: "Cache", widthClass: "hub-table-col-cache", sortable: false },
  { key: "modified", label: "Modified", widthClass: "hub-table-col-date", sortable: true },
  { key: "actions", label: "", widthClass: "hub-table-col-actions", sortable: false },
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
    <div className="hub-table-wrap">
      <Table>
        <TableHead>
          <TableRow>
            {TABLE_COLUMNS.map((column) => {
              const columnSortKey = toSortKey(column.key);
              return (
                <TableHeaderCell key={column.key} className={`hub-table-header ${column.widthClass}`}>
                  {columnSortKey ? (
                    <button type="button" className="hub-table-sort-btn" onClick={() => onSort(columnSortKey)}>
                      {column.label}
                      {sortBy === columnSortKey ? <span className="hub-table-sort-icon">{sortDir === "asc" ? "▲" : "▼"}</span> : null}
                    </button>
                  ) : (
                    <span>{column.label}</span>
                  )}
                </TableHeaderCell>
              );
            })}
          </TableRow>
        </TableHead>
        <TableBody>
          {projects.map((project) => {
            const palette = getProjectPalette(project.project_id);
            return (
              <TableRow key={project.project_id} className="hub-table-row" onClick={() => onOpen(project.project_id)}>
                <TableCell className="hub-table-cell">
                  <div className="hub-project-avatar hub-project-avatar-sm" style={{ background: palette.bg, color: palette.color }}>
                    {project.name.charAt(0).toUpperCase()}
                  </div>
                </TableCell>
                <TableCell className="hub-table-cell">
                  <div className="hub-table-project-name">{project.name}</div>
                  <div className="hub-table-project-desc">{project.description}</div>
                </TableCell>
                <TableCell className="hub-table-cell">
                  <Badge className={`hub-badge-${project.visibility}`}>{project.visibility === "public" ? "◎" : "◉"}</Badge>
                </TableCell>
                <TableCell className="hub-table-cell">
                  <Badge className={`hub-badge-${project.project_type}`}>{project.project_type}</Badge>
                </TableCell>
                <TableCell className="hub-table-cell">
                  <div className="hub-table-tags">
                    {project.tags.slice(0, 2).map((tag) => (
                      <Badge key={tag} className="hub-badge-tag">
                        {tag}
                      </Badge>
                    ))}
                    {project.tags.length > 2 ? <Badge className="hub-project-tag-overflow">+{project.tags.length - 2}</Badge> : null}
                  </div>
                </TableCell>
                <TableCell className="hub-table-cell">{project.model_count}</TableCell>
                <TableCell className="hub-table-cell">{project.sql_count}</TableCell>
                <TableCell className="hub-table-cell">
                  <div className="hub-table-cache">
                    <div className={`hub-cache-dot hub-cache-${project.cache_status}`} />
                    <span className="hub-table-cache-text">{CACHE_LABELS[project.cache_status]}</span>
                  </div>
                </TableCell>
                <TableCell className="hub-table-cell">{formatRelativeDate(project.modified_at)}</TableCell>
                <TableCell className="hub-table-cell">
                  <div className="hub-table-actions">
                    <Button
                      variant="secondary"
                      className="hub-table-action-btn"
                      onClick={(event) => {
                        event.stopPropagation();
                        onEdit(project.project_id);
                      }}
                    >
                      ⚙
                    </Button>
                    <Button
                      variant="secondary"
                      className="hub-table-action-btn"
                      onClick={(event) => {
                        event.stopPropagation();
                        onDelete(project.project_id);
                      }}
                    >
                      ✕
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
