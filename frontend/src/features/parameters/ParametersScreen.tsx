import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";

import {
  createProjectParameter,
  deleteProjectParameter,
  fetchProjectWorkflowStatus,
  fetchProjectParameters,
  fetchProjectTree,
  testProjectParameter,
  updateProjectParameter,
  type FileNode,
  type ProjectParameterItem,
  type ProjectParameterTestResponse,
  type ProjectParameterValueItem,
} from "../../api/projects";
import { useProjectStore } from "../../app/store/projectStore";
import { useUiStore } from "../../app/store/uiStore";

const DOMAIN_TYPES = ["string", "number", "date", "datetime", "bool", "sql.condition", "sql.expression", "sql.identifier"];
const CONTEXT_NAME_PATTERN = /^[A-Za-z0-9_.-]+$/;

function collectModelIds(tree: FileNode | null): string[] {
  if (!tree) return [];
  const stack: FileNode[] = [tree];
  const modelIds: string[] = [];
  while (stack.length > 0) {
    const node = stack.pop();
    if (!node) continue;
    if (node.type === "directory" && node.path.startsWith("model/")) {
      const parts = node.path.split("/").filter(Boolean);
      if (parts.length === 2) {
        modelIds.push(parts[1]);
      }
    }
    const children = node.children ?? [];
    for (const child of children) {
      stack.push(child);
    }
  }
  return Array.from(new Set(modelIds)).sort((a, b) => a.localeCompare(b));
}

function parameterKey(param: Pick<ProjectParameterItem, "name" | "scope">): string {
  return `${param.scope}::${param.name}`;
}

function cloneParameter(param: ProjectParameterItem): ProjectParameterItem {
  return {
    ...param,
    values: Object.fromEntries(
      Object.entries(param.values ?? {}).map(([key, value]) => [
        key,
        { type: value.type, value: value.value },
      ]),
    ),
  };
}

export default function ParametersScreen() {
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const addToast = useUiStore((state) => state.addToast);
  const initialParam = useUiStore((state) => state.initialParam);
  const setInitialParam = useUiStore((state) => state.setInitialParam);
  const queryClient = useQueryClient();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [draft, setDraft] = useState<ProjectParameterItem | null>(null);
  const [isNewDraft, setIsNewDraft] = useState(false);
  const [testContext, setTestContext] = useState("all");
  const [testResult, setTestResult] = useState<ProjectParameterTestResponse | null>(null);
  const [newContextName, setNewContextName] = useState("");

  const paramsQuery = useQuery({
    queryKey: ["projectParameters", currentProjectId],
    queryFn: () => fetchProjectParameters(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });
  const workflowStatusQuery = useQuery({
    queryKey: ["workflowStatus", currentProjectId],
    queryFn: () => fetchProjectWorkflowStatus(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });
  const hasStaleModel = useMemo(
    () => (workflowStatusQuery.data?.models ?? []).some((item) => item.status === "stale"),
    [workflowStatusQuery.data?.models],
  );
  const hasFallbackSource = useMemo(
    () => (workflowStatusQuery.data?.models ?? []).some((item) => item.source === "fallback"),
    [workflowStatusQuery.data?.models],
  );

  const treeQuery = useQuery({
    queryKey: ["projectTree", currentProjectId],
    queryFn: () => fetchProjectTree(currentProjectId as string),
    enabled: Boolean(currentProjectId),
  });

  const modelScopeOptions = useMemo(() => collectModelIds(treeQuery.data ?? null), [treeQuery.data]);
  const parameterItems = paramsQuery.data ?? [];
  const selectedItem = useMemo(
    () => parameterItems.find((item) => parameterKey(item) === selectedKey) ?? null,
    [parameterItems, selectedKey],
  );

  useEffect(() => {
    if (parameterItems.length === 0) {
      setSelectedKey(null);
      if (!isNewDraft) setDraft(null);
      return;
    }
    if (!selectedKey) {
      setSelectedKey(parameterKey(parameterItems[0]));
    }
  }, [parameterItems, selectedKey, isNewDraft]);

  useEffect(() => {
    if (!initialParam || parameterItems.length === 0) return;
    const match =
      parameterItems.find((item) => item.name === initialParam.id && (initialParam.scope === "model" ? item.scope.startsWith("model:") : item.scope === "global")) ??
      parameterItems.find((item) => item.name === initialParam.id) ??
      null;
    if (match) {
      setSelectedKey(parameterKey(match));
    }
    setInitialParam(null);
  }, [initialParam, parameterItems, setInitialParam]);

  useEffect(() => {
    if (!selectedItem || isNewDraft) return;
    setDraft(cloneParameter(selectedItem));
    setTestContext(Object.keys(selectedItem.values ?? {})[0] ?? "all");
    setTestResult(null);
  }, [selectedItem, isNewDraft]);

  const globalItems = useMemo(() => parameterItems.filter((item) => item.scope === "global"), [parameterItems]);
  const localItems = useMemo(() => parameterItems.filter((item) => item.scope.startsWith("model:")), [parameterItems]);

  const isDirty = useMemo(() => {
    if (!draft) return false;
    if (isNewDraft) return true;
    if (!selectedItem) return false;
    return JSON.stringify(draft) !== JSON.stringify(selectedItem);
  }, [draft, isNewDraft, selectedItem]);

  const valuePreview = useMemo(() => {
    if (!draft) return null;
    const selected = draft.values[testContext] ?? draft.values.all ?? draft.values.default ?? Object.values(draft.values)[0] ?? null;
    if (!selected) return null;

    const sourceContext =
      draft.values[testContext] ? testContext : draft.values.all ? "all" : draft.values.default ? "default" : Object.keys(draft.values)[0] ?? testContext;
    const resolvedValueFromTest = testResult && testResult.context === testContext ? testResult.resolved_value : null;
    const resolvedValue = resolvedValueFromTest ?? selected.value;
    return {
      context: testContext,
      sourceContext,
      type: selected.type,
      resolvedValue,
      resolvedByTest: Boolean(resolvedValueFromTest),
    };
  }, [draft, testContext, testResult]);

  const yamlPreview = useMemo(() => {
    if (!draft) return "";
    const escapeValue = (value: string) => value.split('"').join('\\"');
    const lines: string[] = [
      "parameter:",
      `  name: ${draft.name}`,
      `  description: "${escapeValue(draft.description ?? "")}"`,
      `  domain_type: ${draft.domain_type}`,
      "",
      "  values:",
    ];

    for (const [context, row] of Object.entries(draft.values)) {
      lines.push(`    ${context}:`);
      lines.push(`      type: ${row.type}`);
      lines.push(`      value: "${escapeValue(row.value)}"`);
    }
    return lines.join("\n");
  }, [draft]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!currentProjectId || !draft) {
        throw new Error("Project or draft is not selected.");
      }
      if (isNewDraft) {
        return createProjectParameter(currentProjectId, {
          name: draft.name,
          scope: draft.scope,
          description: draft.description,
          domain_type: draft.domain_type,
          values: draft.values,
        });
      }
      if (!selectedItem) {
        throw new Error("Selected parameter is missing.");
      }
      return updateProjectParameter(
        currentProjectId,
        selectedItem.name,
        {
          name: draft.name,
          scope: draft.scope,
          description: draft.description,
          domain_type: draft.domain_type,
          values: draft.values,
        },
        selectedItem.scope,
      );
    },
    onSuccess: async (saved) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projectParameters", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["workflowStatus", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["modelWorkflow", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["autocomplete", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["configChain", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["lineage", currentProjectId] }),
      ]);
      setIsNewDraft(false);
      setSelectedKey(parameterKey(saved));
      setDraft(cloneParameter(saved));
      addToast("Parameter saved", "success");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to save parameter";
      addToast(message, "error");
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      if (!currentProjectId || !draft) {
        throw new Error("Project or parameter is not selected.");
      }
      return testProjectParameter(currentProjectId, draft.name, { context: testContext }, draft.scope);
    },
    onSuccess: (response) => {
      setTestResult(response);
      addToast("Test completed", "success");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to test parameter";
      addToast(message, "error");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!currentProjectId || !selectedItem) {
        throw new Error("Parameter is not selected.");
      }
      await deleteProjectParameter(currentProjectId, selectedItem.name, selectedItem.scope);
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projectParameters", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["workflowStatus", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["modelWorkflow", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["autocomplete", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["configChain", currentProjectId] }),
        queryClient.invalidateQueries({ queryKey: ["lineage", currentProjectId] }),
      ]);
      setDraft(null);
      setSelectedKey(null);
      setIsNewDraft(false);
      setTestResult(null);
      addToast("Parameter deleted", "success");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Failed to delete parameter";
      addToast(message, "error");
    },
  });

  const updateDraft = (patch: Partial<ProjectParameterItem>) => {
    if (!draft) return;
    setDraft({ ...draft, ...patch });
  };

  const updateValue = (context: string, patch: Partial<ProjectParameterValueItem>) => {
    if (!draft) return;
    const current = draft.values[context] ?? { type: "static", value: "" };
    setDraft({
      ...draft,
      values: {
        ...draft.values,
        [context]: {
          type: (patch.type ?? current.type) as "static" | "dynamic",
          value: patch.value ?? current.value,
        },
      },
    });
  };

  const renameContext = (oldContext: string, newContextRaw: string) => {
    if (!draft) return;
    const newContext = newContextRaw.trim();
    if (!newContext || newContext === oldContext) return;
    if (!CONTEXT_NAME_PATTERN.test(newContext)) {
      addToast("Context name allows only letters, numbers, dot, underscore and dash", "error");
      return;
    }
    if (draft.values[newContext]) {
      addToast("Context already exists", "error");
      return;
    }
    const nextValues: Record<string, ProjectParameterValueItem> = {};
    for (const [key, value] of Object.entries(draft.values)) {
      nextValues[key === oldContext ? newContext : key] = value;
    }
    setDraft({ ...draft, values: nextValues });
    if (testContext === oldContext) setTestContext(newContext);
  };

  const removeContext = (context: string) => {
    if (!draft) return;
    const entries = Object.entries(draft.values).filter(([key]) => key !== context);
    const nextValues = Object.fromEntries(entries);
    if (Object.keys(nextValues).length === 0) {
      nextValues.all = { type: "static", value: "" };
    }
    setDraft({ ...draft, values: nextValues });
    if (testContext === context) {
      setTestContext(Object.keys(nextValues)[0]);
    }
  };

  const addContext = () => {
    if (!draft) return;
    const nextContext = newContextName.trim();
    if (!nextContext) {
      addToast("Context name is required", "error");
      return;
    }
    if (!CONTEXT_NAME_PATTERN.test(nextContext)) {
      addToast("Context name allows only letters, numbers, dot, underscore and dash", "error");
      return;
    }
    if (draft.values[nextContext]) {
      addToast("Context already exists", "error");
      return;
    }
    setDraft({
      ...draft,
      values: {
        ...draft.values,
        [nextContext]: { type: "static", value: "" },
      },
    });
    setTestContext(nextContext);
    setNewContextName("");
  };

  const createNew = () => {
    const defaultScope = modelScopeOptions.length > 0 ? `model:${modelScopeOptions[0]}` : "global";
    const next: ProjectParameterItem = {
      name: "new_parameter",
      scope: defaultScope,
      path: "",
      description: "",
      domain_type: "string",
      value_type: "static",
      values: {
        all: { type: "static", value: "" },
      },
    };
    setDraft(next);
    setIsNewDraft(true);
    setSelectedKey(null);
    setTestContext("all");
    setTestResult(null);
  };

  if (!currentProjectId) {
    return (
      <section className="workbench">
        <h1>Parameters Screen</h1>
        <p>Select project to edit parameters.</p>
      </section>
    );
  }

  return (
    <section className="workbench">
      <div className="parameters-head">
        <h1>Parameters</h1>
        <div className="parameters-head-actions">
          <button type="button" className="action-btn" onClick={createNew}>
            New parameter
          </button>
          <button
            type="button"
            className="action-btn"
            disabled={isNewDraft || !selectedItem || deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            {deleteMutation.isPending ? "Deleting..." : "Delete"}
          </button>
          <button
            type="button"
            className="action-btn action-btn-primary"
            disabled={!draft || !isDirty || saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
      <p className="validate-meta">
        Workflow status: {workflowStatusQuery.data?.status ?? "missing"} | Source:{" "}
        {hasFallbackSource ? "fallback" : "framework_cli"} | Stale: {hasStaleModel ? "yes" : "no"}
      </p>

      <div className="parameters-layout">
        <aside className="parameters-list">
          <h2>Global</h2>
          <div className="parameters-list-block">
            {globalItems.length === 0 ? (
              <p className="parameters-empty">No global parameters</p>
            ) : (
              globalItems.map((item) => (
                <button
                  key={parameterKey(item)}
                  type="button"
                  className={selectedKey === parameterKey(item) && !isNewDraft ? "parameters-item parameters-item-active" : "parameters-item"}
                  onClick={() => {
                    setIsNewDraft(false);
                    setSelectedKey(parameterKey(item));
                  }}
                >
                  {item.name}
                </button>
              ))
            )}
          </div>
          <h2>Local</h2>
          <div className="parameters-list-block">
            {localItems.length === 0 ? (
              <p className="parameters-empty">No model parameters</p>
            ) : (
              localItems.map((item) => (
                <button
                  key={parameterKey(item)}
                  type="button"
                  className={selectedKey === parameterKey(item) && !isNewDraft ? "parameters-item parameters-item-active" : "parameters-item"}
                  onClick={() => {
                    setIsNewDraft(false);
                    setSelectedKey(parameterKey(item));
                  }}
                >
                  {item.name}
                  <span className="parameters-item-scope">{item.scope.replace("model:", "")}</span>
                </button>
              ))
            )}
          </div>
        </aside>

        <div className="parameters-editor">
          {!draft ? (
            <p>Select parameter or create new.</p>
          ) : (
            <>
              <section className="model-editor-section">
                <h2>Basic Fields</h2>
                <div className="model-form-grid">
                  <label>
                    Name
                    <input className="ui-input" value={draft.name} onChange={(event) => updateDraft({ name: event.target.value })} />
                  </label>
                  <label>
                    Scope
                    <select className="ui-select" value={draft.scope} onChange={(event) => updateDraft({ scope: event.target.value })}>
                      <option value="global">global</option>
                      {modelScopeOptions.map((modelId) => (
                        <option key={modelId} value={`model:${modelId}`}>
                          model:{modelId}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Domain Type
                    <select className="ui-select" value={draft.domain_type} onChange={(event) => updateDraft({ domain_type: event.target.value })}>
                      {DOMAIN_TYPES.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Description
                    <input className="ui-input" value={draft.description} onChange={(event) => updateDraft({ description: event.target.value })} />
                  </label>
                </div>
              </section>

              <section className="model-editor-section">
                <div className="model-editor-section-head">
                  <h2>Values Table</h2>
                  <div className="parameters-add-context">
                    <input
                      className="ui-input"
                      placeholder="context name"
                      value={newContextName}
                      onChange={(event) => setNewContextName(event.target.value)}
                    />
                    <button type="button" className="action-btn" onClick={addContext}>
                      Add context
                    </button>
                  </div>
                </div>
                <div className="model-attr-table-wrap">
                  <table className="model-attr-table">
                    <thead>
                      <tr>
                        <th>Context</th>
                        <th>Type</th>
                        <th>Value</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(draft.values).map(([context, row]) => (
                        <tr key={context}>
                          <td>
                            <input className="ui-input" value={context} onBlur={(event) => renameContext(context, event.target.value)} />
                          </td>
                          <td>
                            <select
                              className="ui-select"
                              value={row.type}
                              onChange={(event) => updateValue(context, { type: event.target.value as "static" | "dynamic" })}
                            >
                              <option value="static">static</option>
                              <option value="dynamic">dynamic</option>
                            </select>
                          </td>
                          <td>
                            {row.type === "dynamic" ? (
                              <Editor
                                height="120px"
                                language="sql"
                                value={row.value}
                                options={{ minimap: { enabled: false }, fontSize: 12, automaticLayout: true }}
                                onChange={(value) => updateValue(context, { value: value ?? "" })}
                              />
                            ) : (
                              <input
                                className="ui-input"
                                value={row.value}
                                onChange={(event) => updateValue(context, { value: event.target.value })}
                              />
                            )}
                          </td>
                          <td>
                            <button type="button" className="action-btn" onClick={() => removeContext(context)}>
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="model-editor-section">
                <div className="parameters-test-row">
                  <h2>Test Parameter</h2>
                  <div className="parameters-test-actions">
                    <select className="ui-select" value={testContext} onChange={(event) => setTestContext(event.target.value)}>
                      {Object.keys(draft.values).map((context) => (
                        <option key={context} value={context}>
                          {context}
                        </option>
                      ))}
                    </select>
                    <button type="button" className="action-btn" disabled={testMutation.isPending} onClick={() => testMutation.mutate()}>
                      {testMutation.isPending ? "Testing..." : "Test"}
                    </button>
                  </div>
                </div>
                {testResult ? (
                  <pre className="generated-preview">{JSON.stringify(testResult, null, 2)}</pre>
                ) : (
                  <p className="parameters-empty">Run test to see resolved value.</p>
                )}
              </section>

              <section className="model-editor-section">
                <h2>Value Preview</h2>
                {!valuePreview ? (
                  <p className="parameters-empty">No values configured.</p>
                ) : (
                  <div className="parameters-preview-grid">
                    <div>
                      <span className="parameters-preview-label">Context</span>
                      <div>{valuePreview.context}</div>
                    </div>
                    <div>
                      <span className="parameters-preview-label">Source</span>
                      <div>{valuePreview.sourceContext}</div>
                    </div>
                    <div>
                      <span className="parameters-preview-label">Type</span>
                      <div>{valuePreview.type}</div>
                    </div>
                    <div>
                      <span className="parameters-preview-label">Resolved</span>
                      <div className="parameters-preview-value">{valuePreview.resolvedValue}</div>
                    </div>
                    <div>
                      <span className="parameters-preview-label">Mode</span>
                      <div>{valuePreview.resolvedByTest ? "test api" : "draft value"}</div>
                    </div>
                  </div>
                )}
              </section>

              <section className="model-editor-section">
                <h2>YAML Preview</h2>
                <Editor
                  height="260px"
                  language="yaml"
                  value={yamlPreview}
                  options={{ readOnly: true, minimap: { enabled: false }, fontSize: 12, automaticLayout: true }}
                />
              </section>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
