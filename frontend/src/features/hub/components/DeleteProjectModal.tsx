import { useState } from "react";

import type { ProjectListItem } from "../types";

const DELETE_WARNING = {
  internal: "This will permanently delete all project files from the workspace.",
  imported: "This will remove the imported copy from the workspace. The original source directory will not be affected.",
  linked: "This will remove the link from the workspace registry. The original directory at the linked path will not be affected.",
} as const;

interface DeleteProjectModalProps {
  project: ProjectListItem;
  onClose: () => void;
  onSubmit: () => Promise<void>;
  isSubmitting: boolean;
}

export function DeleteProjectModal({ project, onClose, onSubmit, isSubmitting }: DeleteProjectModalProps) {
  const [confirmValue, setConfirmValue] = useState("");
  const canDelete = confirmValue === project.project_id;

  return (
    <div className="hub-overlay" onClick={onClose}>
      <div className="hub-modal hub-modal-sm" onClick={(event) => event.stopPropagation()}>
        <div style={{ padding: "16px 20px", borderBottom: "var(--hub-border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 15, fontWeight: "var(--hub-weight-medium)" }}>Delete project</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, color: "var(--color-text-tertiary)", padding: "2px 6px" }}>
            ✕
          </button>
        </div>

        <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          <div
            style={{
              background: "var(--hub-danger-bg)",
              border: "0.5px solid var(--color-text-danger)",
              borderRadius: 6,
              padding: "12px 14px",
              fontSize: "var(--hub-text-sm)",
              color: "var(--hub-danger-text)",
              lineHeight: 1.6,
            }}
          >
            <strong>You are about to delete {project.name}.</strong> {DELETE_WARNING[project.project_type]} <strong>This action cannot be undone.</strong>
          </div>

          <div>
            <label style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)", display: "block", marginBottom: 4 }}>
              Type project name to confirm:
            </label>
            <input
              className="hub-input"
              placeholder={project.project_id}
              value={confirmValue}
              onChange={(event) => setConfirmValue(event.target.value)}
              style={{
                borderColor:
                  confirmValue === ""
                    ? undefined
                    : canDelete
                      ? "var(--hub-accent-400)"
                      : "var(--hub-danger-border-soft)",
              }}
            />
          </div>
        </div>

        <div style={{ padding: "12px 20px", borderTop: "var(--hub-border-subtle)", background: "var(--hub-surface-panel)", display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="hub-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="hub-btn-danger" disabled={!canDelete || isSubmitting} onClick={onSubmit}>
            {isSubmitting ? "Deleting..." : "Delete project"}
          </button>
        </div>
      </div>
    </div>
  );
}
