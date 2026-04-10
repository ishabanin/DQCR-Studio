import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";

import {
  createProjectModel,
  fetchModelObject,
  fetchModelYmlSchema,
  fetchProjectTree,
  saveModelObject,
  type ModelAttributeItem,
  type ModelObjectResponse,
} from "../../api/projects";
import { getCatalogStatus, type CatalogEntity } from "../../api/catalog";
import { useTheme } from "../../app/providers/themeContext";
import { useEditorStore } from "../../app/store/editorStore";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";
import ProjectStructureDialog, { type ProjectStructureActionState } from "../../shared/components/ProjectStructureDialog";
import Tooltip from "../../shared/components/ui/Tooltip";
import EntityPickerDialog, { type ImportStrategy } from "./EntityPickerDialog";
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

function areModelAttributesEqual(left: ModelAttributeItem | undefined, right: ModelAttributeItem | undefined): boolean {
  if (!left || !right) return false;
  return (
    (left.domain_type ?? "") === (right.domain_type ?? "") &&
    Boolean(left.is_key) === Boolean(right.is_key) &&
    Boolean(left.required) === Boolean(right.required)
  );
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") return fallback;
  const withResponse = error as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = withResponse.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (typeof withResponse.message === "string" && withResponse.message.trim()) return withResponse.message;
  return fallback;
}

function toCatalogAttributes(entity: CatalogEntity): ModelAttributeItem[] {
  return entity.attributes.map((attribute) => ({
    name: attribute.name,
    domain_type: attribute.domain_type,
    is_key: attribute.is_key,
    required: attribute.is_nullable === false,
  }));
}

function mergeModelAttributes(existing: ModelAttributeItem[], incoming: ModelAttributeItem[]): ModelAttributeItem[] {
  const incomingByName = new Map(incoming.map((item) => [item.name, item]));
  const merged: ModelAttributeItem[] = [...incoming];
  for (const item of existing) {
    if (!incomingByName.has(item.name)) {
      merged.push(item);
    }
  }
  return merged;
}

function buildAttributeImportDiff(previous: ModelAttributeItem[], next: ModelAttributeItem[]) {
  const previousByName = new Map(previous.map((item) => [item.name, item]));
  const nextByName = new Map(next.map((item) => [item.name, item]));
  const highlights: Record<string, "added" | "updated"> = {};

  let added = 0;
  let updated = 0;
  let unchanged = 0;

  for (const item of next) {
    const before = previousByName.get(item.name);
    if (!before) {
      added += 1;
      highlights[item.name] = "added";
    } else if (areModelAttributesEqual(before, item)) {
      unchanged += 1;
    } else {
      updated += 1;
      highlights[item.name] = "updated";
    }
  }

  let removed = 0;
  for (const prev of previous) {
    if (!nextByName.has(prev.name)) {
      removed += 1;
    }
  }

  return { added, updated, removed, unchanged, highlights };
}

export default function ModelEditorScreen() {
  const setActiveTab = useEditorStore((state) => state.setActiveTab);
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
  const [createModelState, setCreateModelState] = useState<ProjectStructureActionState | null>(null);
  const [createModelValue, setCreateModelValue] = useState("NewModel");
  const [entityPickerOpen, setEntityPickerOpen] = useState(false);
  const [attributeHighlights, setAttributeHighlights] = useState<Record<string, "added" | "updated">>({});
  const [attributeImportSummary, setAttributeImportSummary] = useState<{
    entityName: string;
    strategy: ImportStrategy;
    added: number;
    updated: number;
    removed: number;
    unchanged: number;
  } | null>(null);
  const formToYamlTimerRef = useRef<number | null>(null);
  const yamlToFormTimerRef = useRef<number | null>(null);
  const attributeHighlightTimerRef = useRef<number | null>(null);

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

  const catalogStatusQuery = useQuery({
    queryKey: ["catalogStatus"],
    queryFn: getCatalogStatus,
  });

  const saveMutation = useMutation({
    mutationFn: (modelPayload: ModelObjectResponse["model"]) =>
      saveModelObject(currentProjectId as string, activeModelId as string, { model: modelPayload }),
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
    },
    onError: (error) => {
      addToast(extractErrorMessage(error, "Failed to save model"), "error");
    },
  });

  const createModelMutation = useMutation({
    mutationFn: (modelId: string) => createProjectModel(currentProjectId as string, modelId),
    onSuccess: async (payload) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projectTree", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["project-info", "tree", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["project-info", "workflow", currentProjectId] }),
      ]);
      setSelectedModelId(payload.model_id);
      setInitialModelId(payload.model_id);
      setDraft(null);
      setMode("visual");
      setYamlText("");
      setYamlError(null);
      setSyncStatus("synced");
      setCreateModelState(null);
      addToast("Model created", "success");
    },
    onError: () => {
      addToast("Failed to create model", "error");
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
      if (attributeHighlightTimerRef.current !== null) {
        window.clearTimeout(attributeHighlightTimerRef.current);
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
    setAttributeHighlights({});
    setAttributeImportSummary(null);

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

  const setTargetTableField = (key: "name" | "table" | "schema" | "description" | "template" | "engine", value: string) => {
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

  const handleImportEntity = (entity: CatalogEntity, strategy: ImportStrategy) => {
    if (!workingModel) return;
    const previousAttributes = [...(workingModel.target_table.attributes ?? [])];
    const importedAttributes = toCatalogAttributes(entity);
    const nextAttributes = strategy === "merge" ? mergeModelAttributes(previousAttributes, importedAttributes) : importedAttributes;
    const diff = buildAttributeImportDiff(previousAttributes, nextAttributes);

    const nextModel: ModelObjectResponse["model"] = {
      ...workingModel,
      target_table: {
        ...workingModel.target_table,
        name: entity.name,
        table: entity.name,
        attributes: nextAttributes,
      },
    };

    setAttributeHighlights(diff.highlights);
    setAttributeImportSummary({
      entityName: entity.name,
      strategy,
      added: diff.added,
      updated: diff.updated,
      removed: diff.removed,
      unchanged: diff.unchanged,
    });
    if (attributeHighlightTimerRef.current !== null) {
      window.clearTimeout(attributeHighlightTimerRef.current);
    }
    attributeHighlightTimerRef.current = window.setTimeout(() => {
      setAttributeHighlights({});
      attributeHighlightTimerRef.current = null;
    }, 12000);

    setDraft(nextModel);
    saveMutation.mutate(nextModel, {
      onSuccess: () => {
        addToast(`${nextAttributes.length} attributes imported from ${entity.name} (${strategy})`, "success");
        setEntityPickerOpen(false);
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
          <button
            type="button"
            className="action-btn"
            onClick={() => {
              setCreateModelValue("NewModel");
              setCreateModelState({ mode: "new-model", path: ".", nodeType: "directory" });
            }}
          >
            New model
          </button>
          <select
            className="ui-select"
            value={activeModelId ?? ""}
            disabled={modelIds.length === 0}
            onChange={(event) => {
              setSelectedModelId(event.target.value || null);
              setDraft(null);
              setMode("visual");
              setYamlError(null);
              setSyncStatus("synced");
            }}
          >
            {modelIds.length === 0 ? <option value="">No models yet</option> : null}
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
            onClick={() => {
              if (!workingModel) return;
              saveMutation.mutate(workingModel, {
                onSuccess: () => {
                  addToast("Model saved", "success");
                },
              });
            }}
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
        <section className="model-editor-empty">
          <span className="model-editor-empty-eyebrow">model/</span>
          <h2>Create a model shell first</h2>
          <p>
            New models start as <code>model/&lt;ModelId&gt;/model.yml</code> with an empty scaffold, so you can fill the structure in visual mode or YAML.
          </p>
          <button
            type="button"
            className="action-btn action-btn-primary"
            onClick={() => {
              setCreateModelValue("NewModel");
              setCreateModelState({ mode: "new-model", path: ".", nodeType: "directory" });
            }}
          >
            Create model
          </button>
        </section>
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
                <HelpLabel text="Table" help="Явное имя физической таблицы назначения (если отличается от Name)." />
                <input
                  className="ui-input"
                  value={workingModel.target_table.table ?? ""}
                  onChange={(event) => setTargetTableField("table", event.target.value)}
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
              <div className="entity-picker-actions">
                <button type="button" className="action-btn" onClick={addAttribute}>
                  Add attribute
                </button>
                {catalogStatusQuery.data?.available ? null : (
                  <button
                    type="button"
                    className="action-btn"
                    onClick={() => {
                      setActiveTab("admin");
                    }}
                  >
                    Open Admin Catalog
                  </button>
                )}
                <button
                  type="button"
                  className="action-btn"
                  disabled={catalogStatusQuery.data?.available !== true || saveMutation.isPending}
                  title={catalogStatusQuery.data?.available ? undefined : "Upload a catalog in Admin or Hub first"}
                  onClick={() => setEntityPickerOpen(true)}
                >
                  {(workingModel.target_table.attributes ?? []).length > 0 ? "Re-import attributes..." : "Import attributes from catalog..."}
                </button>
              </div>
            </div>

            {catalogStatusQuery.data?.meta ? (
              <div className="catalog-muted">
                Catalog: {catalogStatusQuery.data.meta.source_filename} · {catalogStatusQuery.data.meta.entity_count} entities ·{" "}
                {catalogStatusQuery.data.meta.attribute_count} attrs
              </div>
            ) : null}

            {attributeImportSummary ? (
              <div className="model-import-summary">
                Last import from <strong>{attributeImportSummary.entityName}</strong> ({attributeImportSummary.strategy}): +
                {attributeImportSummary.added} / ~{attributeImportSummary.updated} / -{attributeImportSummary.removed} / =
                {attributeImportSummary.unchanged}
              </div>
            ) : null}

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
                      className={
                        attributeHighlights[attr.name] === "added"
                          ? "model-field-row-added"
                          : attributeHighlights[attr.name] === "updated"
                            ? "model-field-row-updated"
                            : undefined
                      }
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

      <EntityPickerDialog
        open={entityPickerOpen}
        existingAttributes={workingModel?.target_table.attributes ?? []}
        onClose={() => setEntityPickerOpen(false)}
        onImport={handleImportEntity}
      />

      <ProjectStructureDialog
        state={createModelState}
        value={createModelValue}
        availableModes={["new-model"]}
        onValueChange={setCreateModelValue}
        onModeChange={() => undefined}
        onCancel={() => setCreateModelState(null)}
        onConfirm={() => {
          const modelId = createModelValue.trim();
          if (!modelId) {
            addToast("Model ID is required", "error");
            return;
          }
          createModelMutation.mutate(modelId);
        }}
        pending={createModelMutation.isPending}
      />
    </section>
  );
}
