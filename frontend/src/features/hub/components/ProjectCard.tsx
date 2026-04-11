import type { MouseEvent } from "react";

import Badge from "../../../shared/components/ui/Badge";
import Button from "../../../shared/components/ui/Button";
import { Card, CardContent, CardFooter, CardHeader } from "../../../shared/components/ui/Card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "../../../shared/components/ui/DropdownMenu";
import Tooltip from "../../../shared/components/ui/Tooltip";
import type { ProjectListItem } from "../types";
import { CACHE_LABELS, formatRelativeDate, getProjectPalette } from "../utils";

interface ProjectCardProps {
  project: ProjectListItem;
  onOpen: (projectId: string) => void;
  onEdit: (projectId: string) => void;
  onDelete: (projectId: string) => void;
  onTagClick: (tag: string) => void;
}

function stopPropagation(event: MouseEvent) {
  event.stopPropagation();
}

export function ProjectCard({ project, onOpen, onEdit, onDelete, onTagClick }: ProjectCardProps) {
  const palette = getProjectPalette(project.project_id);

  return (
    <Card
      className="hub-project-card hub-card-hover"
      onClick={() => onOpen(project.project_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => event.key === "Enter" && onOpen(project.project_id)}
    >
      <CardHeader className="hub-project-head">
        <div className="hub-project-title-row">
          <div className="hub-project-avatar" style={{ background: palette.bg, color: palette.color }}>
            {project.name.charAt(0).toUpperCase()}
          </div>

          <div className="hub-project-title-wrap">
            <div className="hub-project-title">{project.name}</div>
            <div className="hub-project-badges">
              <Badge className={`hub-badge-${project.visibility}`}>{project.visibility === "public" ? "◎ public" : "◉ private"}</Badge>
              <Badge className={`hub-badge-${project.project_type}`}>{project.project_type}</Badge>
            </div>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary" className="hub-project-menu-trigger" onClick={stopPropagation}>
              ⋯
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={stopPropagation} onSelect={() => onEdit(project.project_id)}>
              ⚙ Edit
            </DropdownMenuItem>
            <DropdownMenuItem className="hub-dropdown-item-danger" onClick={stopPropagation} onSelect={() => onDelete(project.project_id)}>
              ✕ Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="hub-project-body">
        <div className="hub-project-description">
          {project.description || <span className="hub-project-description-empty">No description</span>}
        </div>

        {project.tags.length > 0 && (
          <div className="hub-project-tags">
            {project.tags.slice(0, 4).map((tag) => (
              <button
                key={tag}
                type="button"
                className="hub-project-tag-btn"
                onClick={(event) => {
                  stopPropagation(event);
                  onTagClick(tag);
                }}
              >
                <Badge className="hub-badge-tag">{tag}</Badge>
              </button>
            ))}
            {project.tags.length > 4 && <Badge className="hub-project-tag-overflow">+{project.tags.length - 4}</Badge>}
          </div>
        )}

        <div className="hub-project-stats">
          {[
            { label: "models", value: project.model_count },
            { label: "folders", value: project.folder_count },
            { label: "SQL", value: project.sql_count },
          ].map((item) => (
            <span key={item.label} className="hub-project-stat-item">
              <span className="hub-project-stat-value">{item.value}</span> {item.label}
            </span>
          ))}
        </div>
      </CardContent>

      <CardFooter className="hub-project-foot">
        <div className={`hub-cache-dot hub-cache-${project.cache_status}`} />
        <span className="hub-project-cache-label">{CACHE_LABELS[project.cache_status]}</span>
        <Tooltip text={new Date(project.modified_at).toLocaleString("ru")}>
          <span className="hub-project-modified">{formatRelativeDate(project.modified_at)}</span>
        </Tooltip>
      </CardFooter>
    </Card>
  );
}
