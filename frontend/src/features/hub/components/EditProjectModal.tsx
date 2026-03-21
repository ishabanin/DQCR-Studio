import { useState } from "react";

import type { MetadataUpdatePayload, ProjectListItem } from "../types";
import { TagsInput } from "./TagsInput";
import { VisibilitySelector } from "./VisibilitySelector";

interface EditProjectModalProps {
  project: ProjectListItem;
  tagSuggestions: string[];
  onClose: () => void;
  onSubmit: (payload: MetadataUpdatePayload) => Promise<void>;
  isSubmitting: boolean;
}

export function EditProjectModal({ project, tagSuggestions, onClose, onSubmit, isSubmitting }: EditProjectModalProps) {
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description ?? "");
  const [visibility, setVisibility] = useState<"public" | "private">(project.visibility);
  const [tags, setTags] = useState<string[]>(project.tags);

  const handleSubmit = async () => {
    await onSubmit({ name, description, visibility, tags });
  };

  return (
    <div className="hub-overlay" onClick={onClose}>
      <div className="hub-modal" onClick={(event) => event.stopPropagation()}>
        <div style={{ padding: "16px 20px", borderBottom: "var(--hub-border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 15, fontWeight: "var(--hub-weight-medium)" }}>Edit project</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, color: "var(--color-text-tertiary)", padding: "2px 6px" }}>
            ✕
          </button>
        </div>

        <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Project ID
            </label>
            <div
              style={{
                padding: "7px 10px",
                borderRadius: "var(--hub-radius-sm)",
                border: "var(--hub-border-subtle)",
                background: "var(--hub-surface-panel)",
                fontSize: "var(--hub-text-base)",
                fontFamily: "var(--hub-font-mono)",
                color: "var(--color-text-secondary)",
                cursor: "not-allowed",
              }}
            >
              {project.project_id}
            </div>
          </div>

          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Type
            </label>
            <span className={`hub-badge hub-badge-${project.project_type}`}>{project.project_type}</span>
          </div>

          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Display name
            </label>
            <input className="hub-input" value={name} onChange={(event) => setName(event.target.value)} />
          </div>

          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Description
            </label>
            <input className="hub-input" value={description} onChange={(event) => setDescription(event.target.value)} />
          </div>

          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Visibility
            </label>
            <VisibilitySelector value={visibility} onChange={setVisibility} />
          </div>

          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Tags
            </label>
            <TagsInput tags={tags} onChange={setTags} suggestions={tagSuggestions} />
          </div>
        </div>

        <div style={{ padding: "12px 20px", borderTop: "var(--hub-border-subtle)", background: "var(--hub-surface-panel)", display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="hub-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="hub-btn-primary" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
