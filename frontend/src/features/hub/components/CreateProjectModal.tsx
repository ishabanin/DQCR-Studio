import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from "react";

import Button from "../../../shared/components/ui/Button";
import Input from "../../../shared/components/ui/Input";
import Select from "../../../shared/components/ui/Select";
import { DialogBody, DialogFooter } from "../../../shared/components/ui/Dialog";
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "../../../shared/components/ui/Sheet";
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

function useIsMobileSheet() {
  const [isMobile, setIsMobile] = useState<boolean>(() => window.matchMedia("(max-width: 767px)").matches);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const handler = () => setIsMobile(query.matches);
    handler();
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }, []);

  return isMobile;
}

function FormRow({ label, hint, required, children }: { label: string; hint?: string; required?: boolean; children: ReactNode }) {
  return (
    <div className="hub-form-row">
      <label className="hub-form-label">
        {label}
        {required ? <span className="hub-form-required">*</span> : null}
        {hint ? <span className="hub-form-hint">{hint}</span> : null}
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
  const isMobileSheet = useIsMobileSheet();
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
    <Sheet open onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <SheetContent side={isMobileSheet ? "bottom" : "right"} className="hub-sheet">
        <SheetHeader className="hub-sheet-header">
          <SheetTitle>{modeTitle}</SheetTitle>
          <Button variant="ghost" className="hub-dialog-close" onClick={onClose}>
            ✕
          </Button>
        </SheetHeader>

        <div className="hub-dialog-tabs">
          {MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => setActiveMode(mode.id)}
              className={activeMode === mode.id ? "hub-dialog-tab hub-dialog-tab-active" : "hub-dialog-tab"}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <SheetBody className="hub-dialog-scroll">
          <DialogBody className="hub-dialog-body">
            <FormRow label="Project ID" required>
              <Input
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
                onBlur={() => setIdTouched(true)}
                className={idTouched && idError ? "hub-input-error" : ""}
              />
              {idTouched && idError ? <span className="hub-form-error">{idError}</span> : null}
            </FormRow>

            <FormRow label="Display name">
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </FormRow>

            <FormRow label="Description">
              <Input value={description} onChange={(event) => setDescription(event.target.value)} />
            </FormRow>

            {activeMode === "create" ? (
              <>
                <FormRow label="Template">
                  <Select value={template} onChange={(event) => setTemplate(event.target.value as typeof template)}>
                    <option value="flx">flx</option>
                    <option value="dwh_mart">dwh_mart</option>
                    <option value="dq_control">dq_control</option>
                  </Select>
                </FormRow>

                <FormRow label="Visibility">
                  <VisibilitySelector value={visibility} onChange={setVisibility} />
                </FormRow>

                <FormRow label="Tags">
                  <TagsInput tags={tags} onChange={setTags} suggestions={tagSuggestions} />
                </FormRow>
              </>
            ) : (
              <FormRow label="Folder" required hint="Choose local project folder">
                <input
                  ref={folderInputRef}
                  type="file"
                  multiple
                  style={{ display: "none" }}
                  onChange={handleFolderInputChange}
                  {...directoryInputProps}
                />
                <div className="hub-import-row">
                  <Button variant="secondary" onClick={() => folderInputRef.current?.click()}>
                    Choose folder
                  </Button>
                  <span className="hub-import-caption">
                    {uploadFiles.length > 0 ? `${uploadFiles.length} files selected` : "No folder selected"}
                  </span>
                </div>
                {uploadError ? <span className="hub-form-error">{uploadError}</span> : null}
              </FormRow>
            )}
          </DialogBody>
        </SheetBody>

        <SheetFooter>
          <DialogFooter className="hub-dialog-footer">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="default" onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? "Processing..." : submitLabel}
            </Button>
          </DialogFooter>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
