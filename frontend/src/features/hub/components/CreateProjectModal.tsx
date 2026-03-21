import { useMemo, useRef, useState, type ChangeEvent, type ReactNode } from "react";

import type { CreateProjectPayload } from "../types";
import { sanitizeTag } from "../utils";
import { TagsInput } from "./TagsInput";
import { VisibilitySelector } from "./VisibilitySelector";

const MODES = [
  { id: "create", label: "Create new" },
  { id: "import", label: "Import" },
] as const;

function collectUploadRelativePaths(files: File[]): string[] {
  const rawPaths = files.map((file) => {
    const localFile = file as File & { webkitRelativePath?: string; path?: string };
    const relative = typeof localFile.webkitRelativePath === "string" ? localFile.webkitRelativePath.trim() : "";
    if (relative) {
      return relative.replace(/\\/g, "/").replace(/^\/+/, "");
    }
    return file.name;
  });

  const firstSegments = rawPaths
    .map((pathValue) => pathValue.split("/").filter(Boolean))
    .filter((parts) => parts.length > 0)
    .map((parts) => parts[0]);
  const hasNestedPath = rawPaths.some((pathValue) => pathValue.includes("/"));
  const commonRoot = firstSegments.length > 0 && firstSegments.every((segment) => segment === firstSegments[0]) ? firstSegments[0] : null;

  if (commonRoot && hasNestedPath) {
    const normalized = rawPaths.map((pathValue) => (pathValue.startsWith(`${commonRoot}/`) ? pathValue.slice(commonRoot.length + 1) : pathValue));
    if (normalized.some((pathValue) => pathValue === "project.yml" || pathValue.startsWith("contexts/") || pathValue.startsWith("model/"))) {
      return normalized;
    }
  }

  return rawPaths;
}

function FormRow({ label, hint, required, children }: { label: string; hint?: string; required?: boolean; children: ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label
        style={{
          fontSize: "var(--hub-text-sm)",
          fontWeight: "var(--hub-weight-medium)",
          color: "var(--color-text-primary)",
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {label}
        {required && <span style={{ color: "var(--hub-danger-text)" }}>*</span>}
        {hint && <span style={{ fontSize: "var(--hub-text-xs)", fontWeight: "var(--hub-weight-regular)", color: "var(--color-text-tertiary)" }}>{hint}</span>}
      </label>
      {children}
    </div>
  );
}

interface CreateProjectModalProps {
  existingIds: string[];
  tagSuggestions: string[];
  defaultMode?: "create" | "import";
  onClose: () => void;
  onSubmitCreate: (payload: CreateProjectPayload) => Promise<void>;
  onSubmitImport: (payload: {
    files: File[];
    relativePaths: string[];
    project_id?: string;
    name?: string;
    description?: string;
  }) => Promise<void>;
  isSubmitting: boolean;
}

export function CreateProjectModal({
  existingIds,
  tagSuggestions,
  defaultMode = "create",
  onClose,
  onSubmitCreate,
  onSubmitImport,
  isSubmitting,
}: CreateProjectModalProps) {
  const [activeMode, setActiveMode] = useState<"create" | "import">(defaultMode);
  const [projectId, setProjectId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState<"flx" | "dwh_mart" | "dq_control">("flx");
  const [visibility, setVisibility] = useState<"public" | "private">("private");
  const [tags, setTags] = useState<string[]>([]);
  const [idTouched, setIdTouched] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadRelativePaths, setUploadRelativePaths] = useState<string[]>([]);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  const idError = useMemo(() => {
    if (!projectId) return "Project ID is required";
    if (projectId.length < 2) return "At least 2 characters";
    if (projectId.length > 50) return "Maximum 50 characters";
    if (!/^[A-Za-z0-9_-]+$/.test(projectId)) return "Only letters, numbers, underscores and hyphens";
    if (existingIds.map((id) => id.toLowerCase()).includes(projectId.toLowerCase())) return "Project ID already exists";
    return null;
  }, [projectId, existingIds]);

  const uploadError = activeMode === "import" && uploadFiles.length === 0 ? "Choose a folder to import" : null;
  const directoryInputProps = { webkitdirectory: "", directory: "" } as Record<string, string>;

  const handleFolderInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setUploadFiles(files);
    setUploadRelativePaths(collectUploadRelativePaths(files));
  };

  const handleSubmit = async () => {
    setIdTouched(true);
    if (idError) return;

    if (activeMode === "import") {
      if (uploadFiles.length === 0 || uploadRelativePaths.length !== uploadFiles.length) return;
      await onSubmitImport({
        files: uploadFiles,
        relativePaths: uploadRelativePaths,
        project_id: projectId || undefined,
        name: name || undefined,
        description: description || undefined,
      });
      return;
    }

    await onSubmitCreate({
      mode: "create",
      project_id: projectId,
      name: name || projectId,
      description,
      template,
      visibility,
      tags: tags.map(sanitizeTag).filter(Boolean),
    });
  };

  const modeTitle = activeMode === "create" ? "Create project" : "Import project";
  const submitLabel = activeMode === "create" ? "Create project" : "Import";

  return (
    <div className="hub-overlay" onClick={onClose}>
      <div className="hub-modal" onClick={(event) => event.stopPropagation()}>
        <div style={{ display: "flex", borderBottom: "var(--hub-border-subtle)" }}>
          {MODES.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setActiveMode(mode.id)}
              style={{
                flex: 1,
                padding: 10,
                fontSize: "var(--hub-text-sm)",
                textAlign: "center",
                cursor: "pointer",
                color: activeMode === mode.id ? "var(--hub-accent-600)" : "var(--color-text-secondary)",
                background: activeMode === mode.id ? "rgba(29, 158, 117, 0.04)" : "none",
                fontWeight: activeMode === mode.id ? "var(--hub-weight-medium)" : "var(--hub-weight-regular)",
                fontFamily: "var(--hub-font-ui)",
                border: "none",
                borderBottom: `2px solid ${activeMode === mode.id ? "var(--hub-accent-400)" : "transparent"}`,
                transition: "all var(--hub-transition-fast)",
              }}
            >
              {mode.label}
            </button>
          ))}
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 16,
              color: "var(--color-text-tertiary)",
              padding: "2px 10px",
              borderRadius: 4,
              fontFamily: "var(--hub-font-ui)",
            }}
          >
            ✕
          </button>
        </div>

        <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 15, fontWeight: "var(--hub-weight-medium)" }}>{modeTitle}</div>

          <FormRow label="Project ID" required>
            <input
              className="hub-input"
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
              onBlur={() => setIdTouched(true)}
              style={{ borderColor: idTouched && idError ? "var(--hub-danger-text)" : undefined }}
            />
            {idTouched && idError && <span style={{ fontSize: "var(--hub-text-xs)", color: "var(--hub-danger-text)", marginTop: 2 }}>{idError}</span>}
          </FormRow>

          <FormRow label="Display name">
            <input className="hub-input" value={name} onChange={(event) => setName(event.target.value)} />
          </FormRow>

          <FormRow label="Description">
            <input className="hub-input" value={description} onChange={(event) => setDescription(event.target.value)} />
          </FormRow>

          {activeMode === "create" && (
            <>
              <FormRow label="Template">
                <select className="hub-select" value={template} onChange={(event) => setTemplate(event.target.value as typeof template)}>
                  <option value="flx">flx</option>
                  <option value="dwh_mart">dwh_mart</option>
                  <option value="dq_control">dq_control</option>
                </select>
              </FormRow>

              <FormRow label="Visibility">
                <VisibilitySelector value={visibility} onChange={setVisibility} />
              </FormRow>

              <FormRow label="Tags">
                <TagsInput tags={tags} onChange={setTags} suggestions={tagSuggestions} />
              </FormRow>
            </>
          )}

          {activeMode === "import" && (
            <FormRow label="Folder" required hint="Choose local project folder">
              <input
                ref={folderInputRef}
                type="file"
                multiple
                style={{ display: "none" }}
                onChange={handleFolderInputChange}
                {...directoryInputProps}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button className="hub-btn-secondary" type="button" onClick={() => folderInputRef.current?.click()}>
                  Choose folder
                </button>
                <span style={{ fontSize: "var(--hub-text-xs)", color: "var(--color-text-secondary)" }}>
                  {uploadFiles.length > 0 ? `${uploadFiles.length} files selected` : "No folder selected"}
                </span>
              </div>
              {uploadError && <span style={{ fontSize: "var(--hub-text-xs)", color: "var(--hub-danger-text)", marginTop: 2 }}>{uploadError}</span>}
            </FormRow>
          )}
        </div>

        <div
          style={{
            padding: "12px 20px",
            borderTop: "var(--hub-border-subtle)",
            background: "var(--hub-surface-panel)",
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
          }}
        >
          <button className="hub-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="hub-btn-primary" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Processing..." : submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
