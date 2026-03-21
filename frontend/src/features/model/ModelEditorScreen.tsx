import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";

import {
  fetchModelObject,
  fetchModelYmlSchema,
  fetchProjectTree,
  saveModelObject,
  type ModelAttributeItem,
  type ModelObjectResponse,
} from "../../api/projects";
import { useTheme } from "../../app/providers/ThemeProvider";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import Tooltip from "../../shared/components/ui/Tooltip";
import { getDqcrTheme } from "../sql/dqcrLanguage";
import { formToYaml, yamlToForm } from "./syncEngine";
import { areModelsEqual, normalizeYamlText, resolveYamlSyncStatus, type SyncStatus } from "./yamlSync";

type EditorMode = "visual" | "yaml";
function HelpLabel({ text, help }: { text: string; help: string }) {
  return (
    <span className="model-label-wrap">
      <span>{text}</span>
      <Tooltip text={help}>
        <span className="model-help">?</span>
      </Tooltip>
    </span>
  );
}

function collectModelIds(tree: { path: string; type: "file" | "directory"; children?: unknown[] } | null): string[] {
  if (!tree) return [];
  const items: string[] = [];
  const stack = [tree];
  while (stack.length > 0) {
    const node = stack.pop();
    if (!node) continue;
    if (node.type === "directory" && node.path.startsWith("model/")) {
      const parts = node.path.split("/").filter(Boolean);
      if (parts.length === 2) {
        items.push(parts[1]);
      }
    }
    const children = Array.isArray(node.children) ? (node.children as Array<typeof node>) : [];
    for (const child of children) {
      stack.push(child);
    }
  }
  return Array.from(new Set(items)).sort((a, b) => a.localeCompare(b));
}

function normalizeAttrName(value: string, index: number): string {
  const normalized = value.trim();
  if (normalized) return normalized;
  return `field_${index + 1}`;
}

export default function ModelEditorScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const addToast = useUiStore((state) => state.addToast);
  const initialModelId = useUiStore((state) => state.initialModelId);
  const setInitialModelId = useUiStore((state) => state.setInitialModelId);
  const queryClient = useQueryClient();
  const { theme } = useTheme();
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ModelObjectResponse["model"] | null>(null);
  const [draggedAttrIndex, setDraggedAttrIndex] = useState<number | null>(null);
  const [mode, setMode] = useState<EditorMode>("visual");
  const [yamlText, setYamlText] = useState("");
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("synced");
  const formToYamlTimerRef = useRef<number | null>(null);
  const yamlToFormTimerRef = useRef<number | null>(null);

  const treeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });
  const modelIds = useMemo(() => collectModelIds(treeQuery.data ?? null), [treeQuery.data]);
  const activeModelId = selectedModelId ?? modelIds[0] ?? null;

  const schemaQuery = useQuery({
    queryKey: ["modelYmlSchema"],
    queryFn: fetchModelYmlSchema,
  });

  const modelQuery = useQuery({
    queryKey: ["modelObject", currentProjectId, activeModelId],
    queryFn: () => fetchModelObject(currentProjectId as string, activeModelId as string),
    enabled: Boolean(currentProjectId && activeModelId),
  });

  const saveMutation = useMutation({
    mutationFn: () => saveModelObject(currentProjectId as string, activeModelId as string, { model: workingModel as ModelObjectResponse["model"] }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["modelObject", currentProjectId, activeModelId] }),
        queryClient.invalidateQueries({ queryKey: ["workflowStatus", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["modelWorkflow", currentProjectId, activeModelId] }),
        queryClient.invalidateQueries({ queryKey: ["configChain", currentProjectId, activeModelId] }),
        queryClient.invalidateQueries({ queryKey: ["autocomplete", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["lineage", currentProjectId, activeModelId] }),
        queryClient.invalidateQueries({ queryKey: ["projectParameters", currentProjectId] }),
      ]);
      setDraft(null);
      setYamlError(null);
      setSyncStatus("synced");
      addToast("Model saved", "success");
    },
    onError: () => {
      addToast("Failed to save model", "error");
    },
  });

  const sourceModel = modelQuery.data?.model ?? null;
  const workingModel = draft ?? sourceModel;
  const isDirty = useMemo(() => {
    if (!workingModel || !sourceModel) return false;
    return !areModelsEqual(workingModel, sourceModel);
  }, [sourceModel, workingModel]);

  useEffect(() => {
    return () => {
      if (formToYamlTimerRef.current !== null) {
        window.clearTimeout(formToYamlTimerRef.current);
      }
      if (yamlToFormTimerRef.current !== null) {
        window.clearTimeout(yamlToFormTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!initialModelId || modelIds.length === 0) return;
    if (modelIds.includes(initialModelId)) {
      setSelectedModelId(initialModelId);
    }
    setInitialModelId(null);
  }, [initialModelId, modelIds, setInitialModelId]);

  useEffect(() => {
    setDraft(null);
    setDraggedAttrIndex(null);
    setMode("visual");
    setYamlText("");
    setYamlError(null);
    setSyncStatus("synced");

    if (formToYamlTimerRef.current !== null) {
      window.clearTimeout(formToYamlTimerRef.current);
      formToYamlTimerRef.current = null;
    }
    if (yamlToFormTimerRef.current !== null) {
      window.clearTimeout(yamlToFormTimerRef.current);
      yamlToFormTimerRef.current = null;
    }
  }, [activeModelId]);

  useEffect(() => {
    if (!workingModel) {
      setYamlText("");
      setSyncStatus("synced");
      return;
    }
    if (mode !== "visual") return;
    if (formToYamlTimerRef.current !== null) {
      window.clearTimeout(formToYamlTimerRef.current);
    }
    setSyncStatus("syncing");
    formToYamlTimerRef.current = window.setTimeout(() => {
      setYamlText(normalizeYamlText(formToYaml(workingModel)));
      setSyncStatus("synced");
      formToYamlTimerRef.current = null;
    }, 150);
  }, [mode, workingModel]);

  const setTargetTableField = (key: "name" | "schema" | "description" | "template" | "engine", value: string) => {
    if (!workingModel) return;
    const next: ModelObjectResponse["model"] = {
      ...workingModel,
      target_table: {
        ...workingModel.target_table,
        [key]: value,
      },
    };
    setDraft(next);
  };

  const setAttributeField = (
    index: number,
    key: "name" | "domain_type" | "is_key" | "required" | "default_value",
    value: string | boolean,
  ) => {
    if (!workingModel) return;
    const nextAttrs = [...(workingModel.target_table.attributes ?? [])];
    const current = { ...(nextAttrs[index] ?? {}) } as ModelAttributeItem;
    current[key] = value as never;
    nextAttrs[index] = current;
    setDraft({
      ...workingModel,
      target_table: {
        ...workingModel.target_table,
        attributes: nextAttrs,
      },
    });
  };

  const addAttribute = () => {
    if (!workingModel) return;
    const nextAttrs = [...(workingModel.target_table.attributes ?? [])];
    nextAttrs.push({
      name: `new_field_${nextAttrs.length + 1}`,
      domain_type: "string",
      is_key: false,
      required: false,
      default_value: null,
    });
    setDraft({
      ...workingModel,
      target_table: {
        ...workingModel.target_table,
        attributes: nextAttrs,
      },
    });
  };

  const deleteAttribute = (index: number) => {
    if (!workingModel) return;
    const nextAttrs = [...(workingModel.target_table.attributes ?? [])];
    nextAttrs.splice(index, 1);
    setDraft({
      ...workingModel,
      target_table: {
        ...workingModel.target_table,
        attributes: nextAttrs,
      },
    });
  };

  const reorderAttributes = (fromIndex: number, toIndex: number) => {
    if (!workingModel) return;
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
    const nextAttrs = [...(workingModel.target_table.attributes ?? [])];
    const [moved] = nextAttrs.splice(fromIndex, 1);
    nextAttrs.splice(toIndex, 0, moved);
    setDraft({
      ...workingModel,
      target_table: {
        ...workingModel.target_table,
        attributes: nextAttrs,
      },
    });
  };

  if (!currentProjectId) {
    return (
      <section className="workbench">
        <h1>Model Editor</h1>
        <p>Select project to edit model.</p>
      </section>
    );
  }

  return (
    <section className="workbench">
      <div className="model-editor-head">
        <h1>Model Editor</h1>
        <div className="model-editor-head-actions">
          <select
            className="ui-select"
            value={activeModelId ?? ""}
            onChange={(event) => {
              setSelectedModelId(event.target.value || null);
              setDraft(null);
              setMode("visual");
              setYamlError(null);
              setSyncStatus("synced");
            }}
          >
            {modelIds.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <div className="model-mode-switch">
            <button
              type="button"
              className={mode === "visual" ? "action-btn model-mode-active" : "action-btn"}
              onClick={() => {
                if (mode === "yaml" && syncStatus === "conflict") {
                  addToast("Resolve YAML conflict before switching to Visual mode", "error");
                  return;
                }
                setMode("visual");
              }}
            >
              Visual
            </button>
            <button
              type="button"
              className={mode === "yaml" ? "action-btn model-mode-active" : "action-btn"}
              onClick={() => {
                if (workingModel) {
                  setYamlText(formToYaml(workingModel));
                }
                setYamlError(null);
                setSyncStatus("synced");
                setMode("yaml");
              }}
            >
              YAML
            </button>
          </div>
          <button
            type="button"
            className="action-btn action-btn-primary"
            disabled={!activeModelId || !workingModel || !isDirty || saveMutation.isPending || syncStatus === "conflict"}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <div className="model-editor-meta">
        <span>schema: {schemaQuery.isSuccess ? "loaded" : "loading..."}</span>
        <span>dirty: {isDirty ? "yes" : "no"}</span>
        <span
          className={
            syncStatus === "synced"
              ? "model-sync-badge model-sync-badge-synced"
              : syncStatus === "syncing"
                ? "model-sync-badge model-sync-badge-syncing"
                : "model-sync-badge model-sync-badge-conflict"
          }
        >
          {syncStatus}
        </span>
        {yamlError && <span className="model-sync-badge model-sync-badge-conflict">{yamlError}</span>}
      </div>

      {!workingModel ? (
        <p>No model selected.</p>
      ) : mode === "yaml" ? (
        <section className="model-editor-section">
          <h2>YAML Mode</h2>
          <Editor
            height="460px"
            language="yaml"
            theme={getDqcrTheme(theme)}
            value={yamlText}
            options={{
              minimap: { enabled: false },
              fontSize: 11.5,
              lineHeight: 19,
              fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", "Courier New", monospace',
              wordWrap: "on",
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
            onChange={(value) => {
              const next = value ?? "";
              setYamlText(next);
              setSyncStatus("syncing");
              if (yamlToFormTimerRef.current !== null) {
                window.clearTimeout(yamlToFormTimerRef.current);
              }
              yamlToFormTimerRef.current = window.setTimeout(() => {
                const parsed = yamlToForm(next, (schemaQuery.data as Record<string, unknown>) ?? null);
                if (parsed.ok) {
                  setYamlError(null);
                  setSyncStatus(resolveYamlSyncStatus(false));
                  setDraft(parsed.model);
                } else {
                  setYamlError(parsed.error);
                  setSyncStatus(resolveYamlSyncStatus(true));
                }
                yamlToFormTimerRef.current = null;
              }, 300);
            }}
          />
        </section>
      ) : (
        <div className="model-editor-layout">
          <section className="model-editor-section">
            <h2>Target Table</h2>
            <div className="model-form-grid">
              <label>
                <HelpLabel text="Name" help="Имя target table, будет использоваться как физическое имя таблицы." />
                <input
                  className="ui-input"
                  value={workingModel.target_table.name ?? ""}
                  onChange={(event) => setTargetTableField("name", event.target.value)}
                />
              </label>
              <label>
                <HelpLabel text="Schema" help="Схема БД для целевой таблицы, например dm или stg." />
                <input
                  className="ui-input"
                  value={workingModel.target_table.schema ?? ""}
                  onChange={(event) => setTargetTableField("schema", event.target.value)}
                />
              </label>
              <label>
                <HelpLabel text="Description" help="Человекочитаемое описание модели для документации и проверок." />
                <input
                  className="ui-input"
                  value={workingModel.target_table.description ?? ""}
                  onChange={(event) => setTargetTableField("description", event.target.value)}
                />
              </label>
              <label>
                <HelpLabel text="Template" help="Имя шаблона генерации, который определяет дефолтные правила и materialization." />
                <input
                  className="ui-input"
                  value={workingModel.target_table.template ?? ""}
                  onChange={(event) => setTargetTableField("template", event.target.value)}
                />
              </label>
              <label>
                <HelpLabel text="Engine" help="Целевой движок генерации SQL, например dqcr, airflow, dbt или oracle_plsql." />
                <input
                  className="ui-input"
                  value={workingModel.target_table.engine ?? ""}
                  onChange={(event) => setTargetTableField("engine", event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="model-editor-section">
            <div className="model-editor-section-head">
              <h2>Attributes</h2>
              <button type="button" className="action-btn" onClick={addAttribute}>
                Add attribute
              </button>
            </div>
            <div className="model-attr-table-wrap">
              <table className="model-attr-table">
                <thead>
                  <tr>
                    <th>
                      <HelpLabel text="Name" help="Имя атрибута в target table." />
                    </th>
                    <th>
                      <HelpLabel text="Type" help="Domain type атрибута, например string, number, date." />
                    </th>
                    <th>
                      <HelpLabel text="is_key" help="Признак ключевого поля в модели." />
                    </th>
                    <th>
                      <HelpLabel text="required" help="Обязательность заполнения атрибута в целевой записи." />
                    </th>
                    <th>
                      <HelpLabel text="Default" help="Значение по умолчанию, если источник не вернул поле." />
                    </th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(workingModel.target_table.attributes ?? []).map((attr, index) => (
                    <tr
                      key={`${normalizeAttrName(attr.name ?? "", index)}-${index}`}
                      draggable
                      onDragStart={() => setDraggedAttrIndex(index)}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={(event) => {
                        event.preventDefault();
                        if (draggedAttrIndex === null) return;
                        reorderAttributes(draggedAttrIndex, index);
                        setDraggedAttrIndex(null);
                      }}
                    >
                      <td>
                        <input
                          className="ui-input"
                          value={attr.name ?? ""}
                          onChange={(event) => setAttributeField(index, "name", event.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          className="ui-input"
                          value={attr.domain_type ?? ""}
                          onChange={(event) => setAttributeField(index, "domain_type", event.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          type="checkbox"
                          checked={Boolean(attr.is_key)}
                          onChange={(event) => setAttributeField(index, "is_key", event.target.checked)}
                        />
                      </td>
                      <td>
                        <input
                          type="checkbox"
                          checked={Boolean(attr.required)}
                          onChange={(event) => setAttributeField(index, "required", event.target.checked)}
                        />
                      </td>
                      <td>
                        <input
                          className="ui-input"
                          value={attr.default_value == null ? "" : String(attr.default_value)}
                          onChange={(event) => setAttributeField(index, "default_value", event.target.value)}
                        />
                      </td>
                      <td>
                        <button type="button" className="action-btn" onClick={() => deleteAttribute(index)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
