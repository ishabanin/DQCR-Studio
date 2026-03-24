import { type ChangeEvent, type DragEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";

import { createProject, uploadProjectFolder } from "../../api/projects";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";

type TemplateId = "flx" | "dwh_mart" | "dq_control";
type WizardMode = "create" | "import";

const TEMPLATE_CARDS: Array<{ id: TemplateId; title: string; description: string }> = [
  { id: "flx", title: "FLX", description: "Flexible template for general SQL workflows." },
  { id: "dwh_mart", title: "DWH Mart", description: "Warehouse mart-oriented template with analytics defaults." },
  { id: "dq_control", title: "DQ Control", description: "Data quality control pipeline template." },
];

const MODE_CARDS: Array<{ id: WizardMode; title: string; description: string; disabled?: boolean }> = [
  { id: "create", title: "Create New", description: "Generate a new project structure with wizard settings." },
  { id: "import", title: "Upload Folder", description: "Copy an existing local project folder into workspace storage." },
];

interface WizardFormState {
  projectId: string;
  name: string;
  description: string;
  template: TemplateId;
  properties: Array<{ key: string; value: string }>;
  contexts: string[];
  modelName: string;
  firstFolder: string;
  attributes: Array<{ name: string; domain_type: string; is_key: boolean }>;
}

interface SourceFormState {
  sourcePath: string;
  projectId: string;
  name: string;
  description: string;
}

function toSlug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_.-]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "");
}

function makeYamlPreview(state: WizardFormState): string {
  const props = state.properties.filter((item) => item.key.trim());
  const attributes = state.attributes.filter((item) => item.name.trim());
  return [
    `name: ${state.name || "NewProject"}`,
    `description: ${state.description || "Generated via wizard"}`,
    `template: ${state.template}`,
    "",
    "properties:",
    ...(props.length > 0 ? props.map((item) => `  ${item.key}: ${item.value}`) : ["  owner: dq_team"]),
    "",
    "contexts:",
    ...state.contexts.map((ctx) => `  - ${ctx}`),
    "",
    "model:",
    `  name: ${state.modelName}`,
    `  first_folder: ${state.firstFolder}`,
    "  attributes:",
    ...attributes.map((item) => `    - { name: ${item.name}, domain_type: ${item.domain_type}, is_key: ${item.is_key} }`),
  ].join("\n");
}

function makeTreePreview(state: WizardFormState): string[] {
  return [
    `${state.projectId || "<project-id>"}/`,
    "  project.yml",
    "  contexts/",
    ...state.contexts.map((ctx) => `    ${ctx}.yml`),
    "  parameters/",
    "  model/",
    `    ${state.modelName}/`,
    "      model.yml",
    "      workflow/",
    `        ${state.firstFolder}/`,
    "          folder.yml",
    "          001_main.sql",
  ];
}

function validateCreateStep(step: number, state: WizardFormState): string[] {
  if (step === 1) {
    const errors: string[] = [];
    if (!state.name.trim()) errors.push("Project name is required.");
    if (!state.projectId.trim()) errors.push("Project ID is required.");
    if (!/^[a-z0-9][a-z0-9_.-]{1,63}$/.test(state.projectId)) errors.push("Project ID format is invalid.");
    return errors;
  }
  if (step === 2) {
    if (state.contexts.length === 0) return ["At least one context is required."];
    if (!state.contexts.includes("default")) return ["Context list must include default."];
    return [];
  }
  if (step === 3) {
    const errors: string[] = [];
    if (!state.modelName.trim()) errors.push("Model name is required.");
    if (!state.firstFolder.trim()) errors.push("First folder is required.");
    if (state.attributes.filter((item) => item.name.trim()).length === 0) errors.push("Add at least one attribute.");
    return errors;
  }
  return [];
}

function validateSourceState(mode: WizardMode, state: SourceFormState): string[] {
  if (mode === "create") return [];
  const errors: string[] = [];
  if (!state.sourcePath.trim()) errors.push("Source folder path is required.");
  if (state.projectId.trim() && !/^[a-z0-9][a-z0-9_.-]{1,63}$/.test(state.projectId.trim())) errors.push("Project ID format is invalid.");
  return errors;
}

function makeSourcePreview(mode: WizardMode, state: SourceFormState): string[] {
  const modeLabel = "Upload Folder";
  const action = "Files will be copied into internal projects storage.";
  return [
    `Mode: ${modeLabel}`,
    `Source path: ${state.sourcePath || "<not selected>"}`,
    `Project ID: ${state.projectId || "<auto>"}`,
    `Name: ${state.name || "<auto>"}`,
    "",
    "Validation:",
    "  - project.yml exists (server-side check)",
    "  - contexts/ exists (server-side check)",
    "  - model/ exists (server-side check)",
    "",
    `Action: ${action}`,
  ];
}

function inferPathFromFiles(files: File[]): string {
  if (files.length === 0) return "";
  const first = files[0] as File & { path?: string; webkitRelativePath?: string };
  const filePath = typeof first.path === "string" ? first.path.trim() : "";
  const relativePath = typeof first.webkitRelativePath === "string" ? first.webkitRelativePath.trim() : "";
  if (filePath && relativePath) {
    const normalizedFile = filePath.replace(/\\/g, "/");
    const normalizedRelative = relativePath.replace(/\\/g, "/");
    if (normalizedFile.endsWith(normalizedRelative)) {
      const base = normalizedFile.slice(0, normalizedFile.length - normalizedRelative.length).replace(/\/$/, "");
      return base || normalizedFile;
    }
  }
  if (filePath) {
    return filePath.replace(/\\/g, "/");
  }
  if (relativePath) {
    return relativePath.split("/")[0] ?? "";
  }
  return "";
}

function collectUploadRelativePaths(files: File[]): string[] {
  const rawPaths = files.map((file) => {
    const localFile = file as File & { webkitRelativePath?: string; path?: string };
    const relative = typeof localFile.webkitRelativePath === "string" ? localFile.webkitRelativePath.trim() : "";
    if (relative) {
      return relative.replace(/\\/g, "/").replace(/^\/+/, "");
    }
    const pathValue = typeof localFile.path === "string" ? localFile.path.trim() : "";
    if (pathValue) {
      const normalized = pathValue.replace(/\\/g, "/");
      const last = normalized.split("/").filter(Boolean).pop();
      return last ?? file.name;
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

type DirectoryPickerWindow = Window & {
  showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
};
type DirectoryHandleIterable = {
  name?: string;
  values: () => AsyncIterable<FileSystemHandle>;
};

async function collectFilesFromDirectoryHandle(
  handle: FileSystemDirectoryHandle,
): Promise<{ files: File[]; relativePaths: string[] }> {
  const files: File[] = [];
  const relativePaths: string[] = [];

  const walk = async (node: DirectoryHandleIterable, prefix: string) => {
    for await (const entry of node.values()) {
      if (entry.kind === "file") {
        const fileHandle = entry as FileSystemFileHandle;
        const file = await fileHandle.getFile();
        const fileName = fileHandle.name ?? file.name;
        const relative = prefix ? `${prefix}/${fileName}` : fileName;
        files.push(file);
        relativePaths.push(relative);
        continue;
      }
      if (entry.kind === "directory") {
        const directoryHandle = entry as FileSystemDirectoryHandle & DirectoryHandleIterable;
        const nextPrefix = prefix ? `${prefix}/${directoryHandle.name ?? "folder"}` : directoryHandle.name ?? "folder";
        await walk(directoryHandle, nextPrefix);
      }
    }
  };

  await walk(handle as FileSystemDirectoryHandle & DirectoryHandleIterable, "");
  return { files, relativePaths };
}

export default function ProjectWizardModal() {
  const queryClient = useQueryClient();
  const setProjectWizardOpen = useUiStore((state) => state.setProjectWizardOpen);
  const setProject = useProjectStore((state) => state.setProject);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const addToast = useUiStore((state) => state.addToast);

  const [mode, setMode] = useState<WizardMode>("create");
  const [step, setStep] = useState(1);
  const [state, setState] = useState<WizardFormState>({
    projectId: "new-project",
    name: "New Project",
    description: "",
    template: "flx",
    properties: [{ key: "owner", value: "dq_team" }],
    contexts: ["default"],
    modelName: "SampleModel",
    firstFolder: "01_stage",
    attributes: [
      { name: "id", domain_type: "number", is_key: true },
      { name: "description", domain_type: "string", is_key: false },
    ],
  });
  const [sourceState, setSourceState] = useState<SourceFormState>({
    sourcePath: "",
    projectId: "",
    name: "",
    description: "",
  });
  const [newContext, setNewContext] = useState("");
  const [previewTab, setPreviewTab] = useState<"tree" | "yaml">("tree");
  const [isDropActive, setIsDropActive] = useState(false);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadRelativePaths, setUploadRelativePaths] = useState<string[]>([]);
  const createStepErrors = validateCreateStep(step, state);
  const sourceErrors =
    mode === "import"
      ? [
          ...(uploadFiles.length === 0 ? ["Select folder via dialog or drag-and-drop."] : []),
          ...validateSourceState(mode, sourceState).filter((msg) => msg !== "Source folder path is required."),
        ]
      : validateSourceState(mode, sourceState);
  const canGoNext = createStepErrors.length === 0;
  const canSubmitSource = sourceErrors.length === 0;
  const yamlPreview = useMemo(() => makeYamlPreview(state), [state]);
  const treePreview = useMemo(() => makeTreePreview(state), [state]);
  const sourcePreview = useMemo(() => makeSourcePreview(mode, sourceState), [mode, sourceState]);

  const createMutation = useMutation({
    mutationFn: () => {
      if (mode === "create") {
        return createProject({
          mode: "create",
          project_id: state.projectId,
          name: state.name,
          description: state.description,
          template: state.template,
          properties: Object.fromEntries(state.properties.filter((item) => item.key.trim()).map((item) => [item.key, item.value])),
          contexts: state.contexts,
          model: {
            name: state.modelName,
            first_folder: state.firstFolder,
            attributes: state.attributes.map((item) => ({
              name: item.name,
              domain_type: item.domain_type,
              is_key: item.is_key,
            })),
          },
        });
      }
      if (mode === "import" && uploadFiles.length > 0 && uploadRelativePaths.length === uploadFiles.length) {
        return uploadProjectFolder({
          files: uploadFiles,
          relativePaths: uploadRelativePaths,
          project_id: sourceState.projectId.trim() || undefined,
          name: sourceState.name.trim() || undefined,
          description: sourceState.description.trim() || undefined,
        });
      }
      if (mode === "import") {
        throw new Error("No folder files captured. Re-select folder using 'Choose Folder' or drag-and-drop.");
      }
      throw new Error("Unsupported wizard mode.");
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      await queryClient.invalidateQueries({ queryKey: ["projectTree", result.id] });
      await queryClient.invalidateQueries({ queryKey: ["contexts", result.id] });
      setProject(result.id);
      setActiveTab(mode === "import" ? "sql" : "build");
      setProjectWizardOpen(false);
      const actionLabel = mode === "create" ? "created" : "uploaded";
      addToast(`Project ${result.id} ${actionLabel}`, "success");
    },
    onError: (error: unknown) => {
      const axiosError = error as AxiosError<{ detail?: string | Array<{ msg?: string }> }>;
      const detail = axiosError?.response?.data?.detail;
      const detailText = Array.isArray(detail) ? detail.map((item) => item.msg).filter(Boolean).join("; ") : detail;
      const message = typeof detailText === "string" && detailText.trim() ? detailText : error instanceof Error ? error.message : "Failed to submit project request";
      addToast(message, "error");
    },
  });

  const allErrors = mode === "create" ? createStepErrors : sourceErrors;

  useEffect(() => {
    if (!folderInputRef.current) return;
    folderInputRef.current.setAttribute("webkitdirectory", "");
    folderInputRef.current.setAttribute("directory", "");
  }, []);

  const setSourcePathWithNotice = (pathValue: string) => {
    if (!pathValue) {
      addToast("Could not detect folder path. You can paste path manually.", "error");
      return;
    }
    setSourceState((prev) => ({ ...prev, sourcePath: pathValue }));
  };

  const handleFolderDialog = async () => {
    const picker = (window as DirectoryPickerWindow).showDirectoryPicker;
    if (picker) {
      try {
        const handle = await picker();
        const handleWithPath = handle as FileSystemDirectoryHandle & { path?: string };
        const candidatePath = typeof handleWithPath.path === "string" ? handleWithPath.path : "";
        const collected = await collectFilesFromDirectoryHandle(handle);
        if (collected.files.length > 0) {
          setUploadFiles(collected.files);
          setUploadRelativePaths(collected.relativePaths);
          setSourceState((prev) => ({ ...prev, sourcePath: candidatePath || handle.name || prev.sourcePath }));
          addToast(`Selected ${collected.files.length} files from folder`, "success");
          return;
        }
        if (candidatePath) {
          setSourceState((prev) => ({ ...prev, sourcePath: candidatePath }));
          addToast("Folder path selected but no files captured. Try drag-and-drop folder.", "error");
          return;
        }
      } catch {
        // User canceled picker, fallback to file input.
      }
    }
    folderInputRef.current?.click();
  };

  const handleFolderInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setUploadFiles(files);
    setUploadRelativePaths(collectUploadRelativePaths(files));
    const inferredPath = inferPathFromFiles(files);
    setSourcePathWithNotice(inferredPath);
    event.target.value = "";
  };

  const handleDropZoneDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDropActive(false);
    const files = Array.from(event.dataTransfer.files ?? []);
    setUploadFiles(files);
    setUploadRelativePaths(collectUploadRelativePaths(files));
    const inferredPath = inferPathFromFiles(files);
    setSourcePathWithNotice(inferredPath);
  };

  return (
    <div className="wizard-overlay" role="dialog" aria-modal="true">
      <div className="wizard-modal">
        <header className="wizard-head">
          <h2>New Project</h2>
          <button type="button" className="action-btn" onClick={() => setProjectWizardOpen(false)}>
            Close
          </button>
        </header>

        <div className="wizard-mode-switch">
          {MODE_CARDS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={[
                "wizard-mode-card",
                item.id === mode ? "wizard-mode-card-active" : "",
                item.disabled ? "wizard-mode-card-disabled" : "",
              ]
                .join(" ")
                .trim()}
              disabled={item.disabled}
              onClick={() => setMode(item.id)}
            >
              <strong>{item.title}</strong>
              <span>{item.description}</span>
              {item.disabled ? <em>Coming soon</em> : null}
            </button>
          ))}
        </div>

        {mode === "create" ? (
          <div className="wizard-stepper">
            {[1, 2, 3, 4].map((item) => (
              <span key={item} className={item === step ? "wizard-step wizard-step-active" : "wizard-step"}>
                Step {item}
              </span>
            ))}
          </div>
        ) : null}

        <div className="wizard-layout">
          <section className="wizard-content">
            {mode === "create" && step === 1 ? (
              <div className="wizard-grid">
                <label>
                  Name
                  <input
                    className="ui-input"
                    value={state.name}
                    onChange={(event) =>
                      setState((prev) => ({
                        ...prev,
                        name: event.target.value,
                        projectId: toSlug(event.target.value) || prev.projectId,
                      }))
                    }
                  />
                </label>
                <label>
                  Project ID
                  <input className="ui-input" value={state.projectId} onChange={(event) => setState((prev) => ({ ...prev, projectId: toSlug(event.target.value) }))} />
                </label>
                <label>
                  Description
                  <input className="ui-input" value={state.description} onChange={(event) => setState((prev) => ({ ...prev, description: event.target.value }))} />
                </label>
                <div>
                  <p className="wizard-label">Template</p>
                  <div className="wizard-template-list">
                    {TEMPLATE_CARDS.map((card) => (
                      <button
                        key={card.id}
                        type="button"
                        className={state.template === card.id ? "wizard-template wizard-template-active" : "wizard-template"}
                        onClick={() => setState((prev) => ({ ...prev, template: card.id }))}
                      >
                        <strong>{card.title}</strong>
                        <span>{card.description}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="wizard-label">Properties</p>
                  <div className="wizard-list">
                    {state.properties.map((item, index) => (
                      <div key={`${index}-${item.key}`} className="wizard-row">
                        <input
                          className="ui-input"
                          placeholder="key"
                          value={item.key}
                          onChange={(event) =>
                            setState((prev) => ({
                              ...prev,
                              properties: prev.properties.map((entry, i) => (i === index ? { ...entry, key: event.target.value } : entry)),
                            }))
                          }
                        />
                        <input
                          className="ui-input"
                          placeholder="value"
                          value={item.value}
                          onChange={(event) =>
                            setState((prev) => ({
                              ...prev,
                              properties: prev.properties.map((entry, i) => (i === index ? { ...entry, value: event.target.value } : entry)),
                            }))
                          }
                        />
                      </div>
                    ))}
                    <button
                      type="button"
                      className="action-btn"
                      onClick={() => setState((prev) => ({ ...prev, properties: [...prev.properties, { key: "", value: "" }] }))}
                    >
                      Add property
                    </button>
                  </div>
                </div>
              </div>
            ) : null}

            {mode === "create" && step === 2 ? (
              <div>
                <p className="wizard-label">Contexts</p>
                <div className="wizard-list">
                  {state.contexts.map((ctx) => (
                    <div key={ctx} className="wizard-row">
                      <code>{ctx}</code>
                      <button
                        type="button"
                        className="action-btn"
                        disabled={ctx === "default"}
                        onClick={() => setState((prev) => ({ ...prev, contexts: prev.contexts.filter((item) => item !== ctx) }))}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <div className="wizard-row">
                  <input className="ui-input" value={newContext} placeholder="new context" onChange={(event) => setNewContext(toSlug(event.target.value))} />
                  <button
                    type="button"
                    className="action-btn"
                    onClick={() => {
                      const candidate = toSlug(newContext);
                      if (!candidate || state.contexts.includes(candidate)) return;
                      setState((prev) => ({ ...prev, contexts: [...prev.contexts, candidate] }));
                      setNewContext("");
                    }}
                  >
                    Add
                  </button>
                </div>
              </div>
            ) : null}

            {mode === "create" && step === 3 ? (
              <div className="wizard-grid">
                <label>
                  Model name
                  <input className="ui-input" value={state.modelName} onChange={(event) => setState((prev) => ({ ...prev, modelName: event.target.value }))} />
                </label>
                <label>
                  First folder
                  <input className="ui-input" value={state.firstFolder} onChange={(event) => setState((prev) => ({ ...prev, firstFolder: event.target.value }))} />
                </label>
                <div>
                  <p className="wizard-label">Attributes</p>
                  <div className="wizard-list">
                    {state.attributes.map((item, index) => (
                      <div key={`${index}-${item.name}`} className="wizard-row">
                        <input
                          className="ui-input"
                          placeholder="name"
                          value={item.name}
                          onChange={(event) =>
                            setState((prev) => ({
                              ...prev,
                              attributes: prev.attributes.map((entry, i) => (i === index ? { ...entry, name: event.target.value } : entry)),
                            }))
                          }
                        />
                        <input
                          className="ui-input"
                          placeholder="domain_type"
                          value={item.domain_type}
                          onChange={(event) =>
                            setState((prev) => ({
                              ...prev,
                              attributes: prev.attributes.map((entry, i) => (i === index ? { ...entry, domain_type: event.target.value } : entry)),
                            }))
                          }
                        />
                        <label className="wizard-inline-check">
                          <input
                            type="checkbox"
                            checked={item.is_key}
                            onChange={(event) =>
                              setState((prev) => ({
                                ...prev,
                                attributes: prev.attributes.map((entry, i) => (i === index ? { ...entry, is_key: event.target.checked } : entry)),
                              }))
                            }
                          />
                          key
                        </label>
                      </div>
                    ))}
                    <button
                      type="button"
                      className="action-btn"
                      onClick={() =>
                        setState((prev) => ({
                          ...prev,
                          attributes: [...prev.attributes, { name: "", domain_type: "string", is_key: false }],
                        }))
                      }
                    >
                      Add attribute
                    </button>
                  </div>
                </div>
              </div>
            ) : null}

            {mode === "create" && step === 4 ? (
              <div>
                <p className="wizard-label">Confirm and create</p>
                <p className="wizard-note">Review preview on the right, then click Create Project.</p>
              </div>
            ) : null}

            {mode === "import" ? (
              <div className="wizard-grid">
                <input ref={folderInputRef} type="file" className="wizard-folder-hidden-input" onChange={handleFolderInputChange} />
                <div
                  className={isDropActive ? "wizard-dropzone wizard-dropzone-active" : "wizard-dropzone"}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setIsDropActive(true);
                  }}
                  onDragLeave={() => setIsDropActive(false)}
                  onDrop={handleDropZoneDrop}
                >
                  <strong>Drag and drop project folder here</strong>
                  <span>or use folder picker to select a local directory</span>
                  <button type="button" className="action-btn" onClick={handleFolderDialog}>
                    Choose Folder
                  </button>
                </div>
                <label>
                  Local folder path
                  <input
                    className="ui-input"
                    value={sourceState.sourcePath}
                    placeholder="/absolute/path/to/project"
                    onChange={(event) => setSourceState((prev) => ({ ...prev, sourcePath: event.target.value }))}
                  />
                </label>
                <label>
                  Project ID (optional)
                  <input
                    className="ui-input"
                    value={sourceState.projectId}
                    placeholder="auto from name"
                    onChange={(event) => setSourceState((prev) => ({ ...prev, projectId: toSlug(event.target.value) }))}
                  />
                </label>
                <label>
                  Project name (optional)
                  <input
                    className="ui-input"
                    value={sourceState.name}
                    placeholder="auto from project.yml"
                    onChange={(event) => setSourceState((prev) => ({ ...prev, name: event.target.value }))}
                  />
                </label>
                <label>
                  Description (optional)
                  <input
                    className="ui-input"
                    value={sourceState.description}
                    placeholder="only for imported/linked metadata"
                    onChange={(event) => setSourceState((prev) => ({ ...prev, description: event.target.value }))}
                  />
                </label>
              </div>
            ) : null}

            {allErrors.length > 0 ? (
              <ul className="wizard-errors">
                {allErrors.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <aside className="wizard-preview">
            <div className="wizard-preview-head">
              <h3>Live Preview</h3>
              {mode === "create" ? (
                <div className="wizard-preview-tabs">
                  <button
                    type="button"
                    className={previewTab === "tree" ? "wizard-preview-tab wizard-preview-tab-active" : "wizard-preview-tab"}
                    onClick={() => setPreviewTab("tree")}
                  >
                    Tree
                  </button>
                  <button
                    type="button"
                    className={previewTab === "yaml" ? "wizard-preview-tab wizard-preview-tab-active" : "wizard-preview-tab"}
                    onClick={() => setPreviewTab("yaml")}
                  >
                    YAML
                  </button>
                </div>
              ) : null}
            </div>
            {mode === "create" && previewTab === "tree" ? <pre>{treePreview.join("\n")}</pre> : null}
            {mode === "create" && previewTab === "yaml" ? <pre>{yamlPreview}</pre> : null}
            {mode === "import" ? <pre>{sourcePreview.join("\n")}</pre> : null}
          </aside>
        </div>

        <footer className="wizard-footer">
          {mode === "create" ? (
            <>
              <button type="button" className="action-btn" disabled={step <= 1} onClick={() => setStep((prev) => Math.max(1, prev - 1))}>
                Back
              </button>
              {step < 4 ? (
                <button type="button" className="action-btn action-btn-primary" disabled={!canGoNext} onClick={() => setStep((prev) => Math.min(4, prev + 1))}>
                  Next
                </button>
              ) : (
                <button type="button" className="action-btn action-btn-primary" disabled={createMutation.isPending} onClick={() => createMutation.mutate()}>
                  {createMutation.isPending ? "Creating..." : "Create Project"}
                </button>
              )}
            </>
          ) : (
            <>
              <button type="button" className="action-btn" onClick={() => setProjectWizardOpen(false)}>
                Cancel
              </button>
              <button type="button" className="action-btn action-btn-primary" disabled={createMutation.isPending || !canSubmitSource} onClick={() => createMutation.mutate()}>
                {createMutation.isPending ? "Processing..." : "Upload Project"}
              </button>
            </>
          )}
        </footer>
      </div>
    </div>
  );
}
