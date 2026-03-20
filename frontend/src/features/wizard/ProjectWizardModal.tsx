import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createProject } from "../../api/projects";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";

type TemplateId = "flx" | "dwh_mart" | "dq_control";

const TEMPLATE_CARDS: Array<{ id: TemplateId; title: string; description: string }> = [
  { id: "flx", title: "FLX", description: "Flexible template for general SQL workflows." },
  { id: "dwh_mart", title: "DWH Mart", description: "Warehouse mart-oriented template with analytics defaults." },
  { id: "dq_control", title: "DQ Control", description: "Data quality control pipeline template." },
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

function validateStep(step: number, state: WizardFormState): string[] {
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

export default function ProjectWizardModal() {
  const queryClient = useQueryClient();
  const setProjectWizardOpen = useUiStore((state) => state.setProjectWizardOpen);
  const setProject = useProjectStore((state) => state.setProject);
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
  const addToast = useUiStore((state) => state.addToast);
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
  const [newContext, setNewContext] = useState("");
  const [previewTab, setPreviewTab] = useState<"tree" | "yaml">("tree");
  const stepErrors = validateStep(step, state);
  const canGoNext = stepErrors.length === 0;
  const yamlPreview = useMemo(() => makeYamlPreview(state), [state]);
  const treePreview = useMemo(() => makeTreePreview(state), [state]);

  const createMutation = useMutation({
    mutationFn: () =>
      createProject({
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
      }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      await queryClient.invalidateQueries({ queryKey: ["projectTree", result.id] });
      await queryClient.invalidateQueries({ queryKey: ["contexts", result.id] });
      setProject(result.id);
      setActiveTab("build");
      setProjectWizardOpen(false);
      addToast(`Project ${result.id} created`, "success");
    },
    onError: () => addToast("Failed to create project", "error"),
  });

  return (
    <div className="wizard-overlay" role="dialog" aria-modal="true">
      <div className="wizard-modal">
        <header className="wizard-head">
          <h2>Create Project</h2>
          <button type="button" className="action-btn" onClick={() => setProjectWizardOpen(false)}>
            Close
          </button>
        </header>

        <div className="wizard-stepper">
          {[1, 2, 3, 4].map((item) => (
            <span key={item} className={item === step ? "wizard-step wizard-step-active" : "wizard-step"}>
              Step {item}
            </span>
          ))}
        </div>

        <div className="wizard-layout">
          <section className="wizard-content">
            {step === 1 ? (
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

            {step === 2 ? (
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

            {step === 3 ? (
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

            {step === 4 ? (
              <div>
                <p className="wizard-label">Confirm and create</p>
                <p className="wizard-note">Review preview on the right, then click Create Project.</p>
              </div>
            ) : null}

            {stepErrors.length > 0 ? (
              <ul className="wizard-errors">
                {stepErrors.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <aside className="wizard-preview">
            <div className="wizard-preview-head">
              <h3>Live Preview</h3>
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
            </div>
            {previewTab === "tree" ? <pre>{treePreview.join("\n")}</pre> : null}
            {previewTab === "yaml" ? <pre>{yamlPreview}</pre> : null}
          </aside>
        </div>

        <footer className="wizard-footer">
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
        </footer>
      </div>
    </div>
  );
}
