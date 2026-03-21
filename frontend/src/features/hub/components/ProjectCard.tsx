import type { MouseEvent, ReactNode } from "react";

import type { ProjectListItem } from "../types";
import { CACHE_LABELS, formatRelativeDate, getProjectPalette } from "../utils";

interface ProjectCardProps {
  project: ProjectListItem;
  onOpen: (projectId: string) => void;
  onEdit: (projectId: string) => void;
  onDelete: (projectId: string) => void;
  onTagClick: (tag: string) => void;
}

interface ActionButtonProps {
  children: ReactNode;
  title: string;
  danger?: boolean;
  onClick: (event: MouseEvent<HTMLButtonElement>) => void;
}

function ActionButton({ children, title, danger, onClick }: ActionButtonProps) {
  return (
    <button
      title={title}
      onClick={onClick}
      style={{
        width: 26,
        height: 26,
        borderRadius: 5,
        background: "var(--hub-surface-card)",
        border: "var(--hub-border-medium)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12,
        cursor: "pointer",
        color: "var(--color-text-secondary)",
        transition: "color var(--hub-transition-fast), background var(--hub-transition-fast), border-color var(--hub-transition-fast)",
      }}
      onMouseEnter={(event) => {
        if (danger) {
          event.currentTarget.style.color = "var(--hub-danger-text)";
          event.currentTarget.style.background = "var(--hub-danger-bg)";
          event.currentTarget.style.borderColor = "var(--hub-danger-border-soft)";
        } else {
          event.currentTarget.style.color = "var(--color-text-primary)";
          event.currentTarget.style.background = "var(--hub-surface-panel)";
        }
      }}
      onMouseLeave={(event) => {
        event.currentTarget.style.color = "";
        event.currentTarget.style.background = "";
        event.currentTarget.style.borderColor = "";
      }}
    >
      {children}
    </button>
  );
}

export function ProjectCard({ project, onOpen, onEdit, onDelete, onTagClick }: ProjectCardProps) {
  const palette = getProjectPalette(project.project_id);

  return (
    <div
      className="hub-project-card hub-card-hover"
      onClick={() => onOpen(project.project_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => event.key === "Enter" && onOpen(project.project_id)}
      style={{
        background: "var(--hub-surface-card)",
        border: "var(--hub-border-subtle)",
        borderRadius: "var(--hub-radius-card)",
        overflow: "hidden",
        cursor: "pointer",
        position: "relative",
      }}
    >
      <div style={{ padding: "12px var(--hub-card-px) 10px", borderBottom: "var(--hub-border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "var(--hub-radius-md)",
              background: palette.bg,
              color: palette.color,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: "var(--hub-weight-medium)",
              flexShrink: 0,
            }}
          >
            {project.name.charAt(0).toUpperCase()}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: "var(--hub-text-base)",
                fontWeight: "var(--hub-weight-medium)",
                color: "var(--color-text-primary)",
                lineHeight: 1.2,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {project.name}
            </div>
            <div style={{ display: "flex", gap: 4, marginTop: 4, flexWrap: "wrap" }}>
              <span className={`hub-badge hub-badge-${project.visibility}`}>{project.visibility === "public" ? "◎ public" : "◉ private"}</span>
              <span className={`hub-badge hub-badge-${project.project_type}`}>{project.project_type}</span>
            </div>
          </div>
        </div>

        <div
          style={{
            fontSize: "var(--hub-text-xs)",
            color: "var(--color-text-secondary)",
            lineHeight: 1.45,
            marginBottom: 8,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {project.description || <span style={{ color: "var(--color-text-tertiary)", fontStyle: "italic" }}>No description</span>}
        </div>

        {project.tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {project.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="hub-badge hub-badge-tag"
                onClick={(event) => {
                  event.stopPropagation();
                  onTagClick(tag);
                }}
                style={{ cursor: "pointer" }}
              >
                {tag}
              </span>
            ))}
            {project.tags.length > 4 && (
              <span className="hub-badge" style={{ background: "var(--hub-surface-panel)", color: "var(--color-text-tertiary)" }}>
                +{project.tags.length - 4}
              </span>
            )}
          </div>
        )}
      </div>

      <div style={{ padding: "8px var(--hub-card-px)", display: "flex", gap: 14 }}>
        {[
          { label: "models", value: project.model_count },
          { label: "folders", value: project.folder_count },
          { label: "SQL", value: project.sql_count },
        ].map((s) => (
          <span key={s.label} style={{ fontSize: "var(--hub-text-xs)", color: "var(--color-text-secondary)" }}>
            <span style={{ fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)" }}>{s.value}</span> {s.label}
          </span>
        ))}
      </div>

      <div
        style={{
          padding: "7px var(--hub-card-px)",
          background: "var(--hub-surface-panel)",
          borderTop: "var(--hub-border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <div className={`hub-cache-dot hub-cache-${project.cache_status}`} />
        <span style={{ fontSize: "var(--hub-text-2xs)", color: "var(--color-text-tertiary)", flex: 1 }}>{CACHE_LABELS[project.cache_status]}</span>
        <span style={{ fontSize: "var(--hub-text-2xs)", color: "var(--color-text-tertiary)" }}>{formatRelativeDate(project.modified_at)}</span>
      </div>

      <div className="hub-card-actions" style={{ position: "absolute", top: 10, right: 10, display: "flex", gap: 4 }}>
        <ActionButton
          title="Settings"
          onClick={(event) => {
            event.stopPropagation();
            onEdit(project.project_id);
          }}
        >
          ⚙
        </ActionButton>
        <ActionButton
          title="Delete"
          danger
          onClick={(event) => {
            event.stopPropagation();
            onDelete(project.project_id);
          }}
        >
          ✕
        </ActionButton>
      </div>
    </div>
  );
}
