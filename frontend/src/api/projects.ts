import { apiClient } from "./client";

export interface ProjectItem {
  id: string;
  name: string;
  description?: string | null;
  project_type?: "internal" | "imported" | "linked";
  source_type?: "internal" | "imported" | "linked";
  source_path?: string | null;
  availability_status?: "available" | "unavailable";
  visibility?: "public" | "private";
  tags?: string[];
  cache_status?: "ready" | "stale" | "building" | "error" | "missing";
  model_count?: number;
  folder_count?: number;
  sql_count?: number;
  modified_at?: string;
}

export interface ContextItem {
  id: string;
  name: string;
}

export interface CreateProjectResponse {
  id: string;
  name: string;
  path: string;
  contexts: string[];
  model: string;
  source_type?: "internal" | "imported" | "linked";
  source_path?: string | null;
  availability_status?: "available" | "unavailable";
}

export interface MetadataUpdatePayload {
  name?: string;
  description?: string;
  visibility?: "public" | "private";
  tags?: string[];
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
}

export interface CreateProjectModelResponse {
  status: string;
  path: string;
  model_id: string;
  file_path: string;
}

export interface AutocompleteParameterItem {
  name: string;
  scope: string;
  path: string;
  domain_type: string | null;
  value_type: string | null;
}

export interface AutocompleteMacroItem {
  name: string;
  source: string;
}

export interface AutocompleteObjectColumnItem {
  name: string;
  domain_type: string | null;
  is_key: boolean | null;
}

export interface AutocompleteObjectItem {
  name: string;
  kind: "target_table" | "workflow_query" | "catalog_entity";
  source: "project_workflow" | "project_model_fallback" | "catalog";
  model_id: string | null;
  path: string | null;
  lookup_keys: string[];
  columns: AutocompleteObjectColumnItem[];
}

export interface ProjectAutocompleteResponse {
  parameters: AutocompleteParameterItem[];
  macros: AutocompleteMacroItem[];
  config_keys: string[];
  objects: AutocompleteObjectItem[];
  all_contexts?: string[];
  data_source?: "workflow" | "fallback";
  fallback?: boolean;
}

export interface LineageNode {
  id: string;
  name: string;
  path: string;
  materialized: string;
  enabled_contexts: string[] | null;
  queries: string[];
  parameters: string[];
  ctes: string[];
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  status: string;
}

export interface LineageSummary {
  folders: number;
  queries: number;
  params: number;
}

export interface LineageResponse {
  project_id: string;
  model_id: string;
  nodes: LineageNode[];
  edges: LineageEdge[];
  summary: LineageSummary;
}

export interface ConfigChainLevel {
  id: "template" | "project" | "model" | "folder" | "sql";
  label: string;
  source_path: string | null;
  values: Record<string, string | null>;
}

export interface ConfigChainResolvedItem {
  key: string;
  value: string | null;
  source_level: ConfigChainLevel["id"];
  overridden_levels: ConfigChainLevel["id"][];
}

export interface ConfigChainResponse {
  project_id: string;
  model_id: string;
  sql_path: string | null;
  levels: ConfigChainLevel[];
  resolved: ConfigChainResolvedItem[];
  cte_settings: {
    default: string | null;
    by_context: Record<string, string>;
  };
  generated_outputs: string[];
  sql_metadata?: {
    parameters: string[];
    ctes: string[];
    inline_cte_configs: Record<string, string>;
  };
  data_source?: "workflow" | "fallback";
  fallback?: boolean;
  workflow_status?: string;
  workflow_source?: string;
  workflow_updated_at?: string | null;
}

export interface BuildPreviewResponse {
  project_id: string;
  model_id: string;
  engine: string;
  sql_path: string;
  preview: string;
}

export interface BuildGeneratedFileItem {
  path: string;
  source_path: string | null;
  size_bytes: number;
}

export interface BuildRunResult {
  build_id: string;
  timestamp: string;
  project: string;
  model: string;
  engine: "dqcr" | "airflow" | "dbt" | "oracle_plsql";
  context: string;
  dry_run: boolean;
  output_path: string;
  files_count: number;
  files: BuildGeneratedFileItem[];
  workflow_updated_at?: string | null;
  workflow_status?: string;
  workflow_source?: string;
}

export interface BuildFilesTreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  size_bytes?: number;
  source_path?: string;
  children?: BuildFilesTreeNode[];
}

export interface BuildFilesResponse {
  project_id: string;
  build_id: string;
  engine: string;
  output_path: string;
  files: BuildGeneratedFileItem[];
  tree: BuildFilesTreeNode;
}

export interface AdminTemplateFolderRule {
  name: string;
  materialized: string;
  enabled: boolean;
}

export interface AdminTemplateResponse {
  name: string;
  content: string;
  rules: {
    folders: AdminTemplateFolderRule[];
  };
}

export interface AdminRuleItem {
  id: string;
  name: string;
  severity: "pass" | "warning" | "error";
  enabled: boolean;
  pattern: string;
  description: string;
}

export interface AdminMacroItem {
  name: string;
  source: string;
  description: string;
}

export interface BuildFileContentResponse {
  build_id: string;
  path: string;
  content: string;
}

export interface ValidationRuleResult {
  rule_id: string;
  name: string;
  status: "pass" | "warning" | "error";
  message: string;
  file_path: string | null;
  line: number | null;
}

export interface ValidationRunResult {
  run_id: string;
  timestamp: string;
  project: string;
  model: string;
  summary: {
    passed: number;
    warnings: number;
    errors: number;
  };
  rules: ValidationRuleResult[];
  workflow_updated_at?: string | null;
  workflow_status?: string;
  workflow_source?: string;
}

export interface WorkflowModelState {
  project_id: string;
  model_id: string;
  status: "ready" | "stale" | "building" | "error" | "missing";
  updated_at: string | null;
  error: string | null;
  source: "framework_cli" | "fallback";
  workflow?: Record<string, unknown> | null;
}

export type WorkflowStatus = "ready" | "stale" | "building" | "error" | "missing";

export interface WorkflowProjectStatus {
  project_id: string;
  status?: WorkflowStatus;
  overall?: WorkflowStatus;
  models: Array<{
    project_id: string;
    model_id: string;
    status: WorkflowStatus;
    updated_at: string | null;
    error: string | null;
    source: "framework_cli" | "fallback";
    has_cache: boolean;
  }>;
}

export interface ValidationQuickFixResponse {
  project_id: string;
  model_id: string;
  type: "add_field" | "rename_folder";
  applied: boolean;
  message: string;
  changed_files: string[];
  validation: ValidationRunResult | null;
}

export interface ValidationQuickFixDryRunResponse {
  file_path: string;
  diff: string;
  description: string;
}

export interface ProjectParameterValueItem {
  type: "static" | "dynamic";
  value: string;
}

export interface ProjectParameterItem {
  name: string;
  scope: string;
  path: string;
  description: string;
  domain_type: string;
  value_type: string;
  values: Record<string, ProjectParameterValueItem>;
}

export interface ProjectParameterTestResponse {
  ok: boolean;
  parameter: string;
  scope: string;
  context: string;
  type: "static" | "dynamic";
  resolved_value: string;
}

export interface ModelAttributeItem {
  name: string;
  domain_type?: string | null;
  is_key?: boolean | null;
  required?: boolean | null;
  default_value?: string | number | boolean | null;
}

export interface ModelFolderItem {
  id: string;
  description?: string | null;
  enabled?: boolean | null;
  materialization?: string | null;
  pattern?: string | null;
}

export interface ModelObjectResponse {
  project_id: string;
  model_id: string;
  path: string;
  data_source?: "workflow" | "fallback";
  workflow_status?: string;
  workflow_source?: string;
  workflow_updated_at?: string | null;
  model: {
    target_table: {
      name?: string | null;
      table?: string | null;
      schema?: string | null;
      description?: string | null;
      template?: string | null;
      engine?: string | null;
      attributes: ModelAttributeItem[];
    };
    workflow: {
      description?: string | null;
      folders: ModelFolderItem[];
    };
    cte_settings?: {
      default?: string | null;
      by_context?: Record<string, string>;
    };
  };
}

export type ModelYmlSchemaResponse = Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeFileNode(value: unknown, fallbackName = "project", fallbackPath = "."): FileNode {
  if (!isRecord(value)) {
    return { name: fallbackName, path: fallbackPath, type: "directory", children: [] };
  }

  const type = value.type === "file" ? "file" : "directory";
  const name = typeof value.name === "string" && value.name.trim() ? value.name : fallbackName;
  const path = typeof value.path === "string" && value.path.trim() ? value.path : fallbackPath;
  const childrenRaw = Array.isArray(value.children) ? value.children : [];
  return {
    name,
    path,
    type,
    children: type === "directory" ? childrenRaw.map((child) => normalizeFileNode(child, "item", "")).filter(Boolean) : undefined,
  };
}

function normalizeBuildFileNode(value: unknown, fallbackName = "output", fallbackPath = ""): BuildFilesTreeNode {
  if (!isRecord(value)) {
    return { name: fallbackName, path: fallbackPath, type: "directory", children: [] };
  }
  const type = value.type === "file" ? "file" : "directory";
  const name = typeof value.name === "string" && value.name.trim() ? value.name : fallbackName;
  const path = typeof value.path === "string" ? value.path : fallbackPath;
  const sourcePath = typeof value.source_path === "string" ? value.source_path : undefined;
  const sizeBytes = typeof value.size_bytes === "number" ? value.size_bytes : undefined;
  const childrenRaw = Array.isArray(value.children) ? value.children : [];
  return {
    name,
    path,
    type,
    size_bytes: sizeBytes,
    source_path: sourcePath,
    children: type === "directory" ? childrenRaw.map((child) => normalizeBuildFileNode(child, "item", "")) : undefined,
  };
}

export async function fetchProjects(): Promise<ProjectItem[]> {
  const { data } = await apiClient.get<ProjectItem[]>("/projects");
  if (!Array.isArray(data)) return [];
  return data.filter((item): item is ProjectItem => isRecord(item) && typeof item.id === "string" && typeof item.name === "string");
}

export async function fetchProject(projectId: string): Promise<ProjectItem> {
  const { data } = await apiClient.get<ProjectItem>(`/projects/${projectId}`);
  return data;
}

export async function patchProjectMetadata(projectId: string, payload: MetadataUpdatePayload): Promise<{ ok: boolean }> {
  const { data } = await apiClient.patch<{ ok: boolean }>(`/projects/${projectId}/metadata`, payload);
  return data;
}

export async function deleteProject(projectId: string): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(`/projects/${projectId}`);
  return data;
}

export async function createProject(payload: {
  mode?: "create" | "import" | "connect";
  project_id?: string;
  name?: string;
  description?: string;
  template?: "flx" | "dwh_mart" | "dq_control";
  properties?: Record<string, string>;
  contexts?: string[];
  source_path?: string;
  model?: {
    name: string;
    first_folder: string;
    attributes: Array<{ name: string; domain_type: string; is_key?: boolean }>;
  };
}): Promise<CreateProjectResponse> {
  const { data } = await apiClient.post<CreateProjectResponse>("/projects", payload);
  return data;
}

export async function uploadProjectFolder(payload: {
  files: File[];
  relativePaths: string[];
  project_id?: string;
  name?: string;
  description?: string;
}): Promise<CreateProjectResponse> {
  const formData = new FormData();
  payload.files.forEach((file) => {
    formData.append("files", file, file.name);
  });
  payload.relativePaths.forEach((relativePath) => {
    formData.append("relative_paths", relativePath);
  });
  if (payload.project_id) formData.append("project_id", payload.project_id);
  if (payload.name) formData.append("name", payload.name);
  if (payload.description) formData.append("description", payload.description);
  const { data } = await apiClient.post<CreateProjectResponse>("/projects/import-upload", formData, {
    // Folder upload can exceed default 10s timeout on large projects.
    timeout: 120000,
  });
  return data;
}

export async function fetchProjectTree(projectId: string): Promise<FileNode> {
  const { data } = await apiClient.get<FileNode>(`/projects/${projectId}/files/tree`);
  return normalizeFileNode(data, projectId, ".");
}

export async function fetchProjectContexts(projectId: string): Promise<ContextItem[]> {
  const { data } = await apiClient.get<ContextItem[]>(`/projects/${projectId}/contexts`);
  if (!Array.isArray(data)) {
    return [{ id: "default", name: "default" }];
  }
  const normalized = data.filter((item): item is ContextItem => isRecord(item) && typeof item.id === "string" && typeof item.name === "string");
  return normalized.length > 0 ? normalized : [{ id: "default", name: "default" }];
}

export async function renameProjectPath(projectId: string, path: string, newName: string): Promise<void> {
  await apiClient.post(`/projects/${projectId}/files/rename`, { path, new_name: newName });
}

export async function deleteProjectPath(projectId: string, path: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/files`, { params: { path } });
}

export async function createProjectFolder(projectId: string, path: string): Promise<void> {
  await apiClient.post(`/projects/${projectId}/files/folder`, { path });
}

export async function createProjectModel(projectId: string, modelId: string): Promise<CreateProjectModelResponse> {
  const { data } = await apiClient.post<CreateProjectModelResponse>(`/projects/${projectId}/files/model`, { model_id: modelId });
  return data;
}

export async function fetchFileContent(projectId: string, path: string): Promise<string> {
  const { data } = await apiClient.get<{ path: string; content: string }>(`/projects/${projectId}/files/content`, {
    params: { path },
  });
  return data.content;
}

export async function saveFileContent(projectId: string, path: string, content: string): Promise<void> {
  await apiClient.put(`/projects/${projectId}/files/content`, { path, content });
}

export async function fetchProjectAutocomplete(projectId: string, modelId?: string | null): Promise<ProjectAutocompleteResponse> {
  const { data } = await apiClient.get<ProjectAutocompleteResponse>(`/projects/${projectId}/autocomplete`, {
    params: modelId ? { model_id: modelId } : undefined,
  });
  return data;
}

export async function fetchProjectWorkflowStatus(projectId: string): Promise<WorkflowProjectStatus> {
  const { data } = await apiClient.get<WorkflowProjectStatus>(`/projects/${projectId}/workflow/status`);
  return data;
}

export async function fetchModelWorkflow(projectId: string, modelId: string): Promise<WorkflowModelState> {
  const { data } = await apiClient.get<WorkflowModelState>(`/projects/${projectId}/models/${modelId}/workflow`);
  return data;
}

export async function rebuildModelWorkflow(projectId: string, modelId: string): Promise<WorkflowModelState> {
  const { data } = await apiClient.post<WorkflowModelState>(`/projects/${projectId}/models/${modelId}/workflow/rebuild`);
  return data;
}

export async function fetchModelLineage(projectId: string, modelId: string, context?: string): Promise<LineageResponse> {
  const params = context && context.trim() ? { context: context.trim() } : undefined;
  const { data } = await apiClient.get<LineageResponse>(`/projects/${projectId}/models/${modelId}/lineage`, { params });
  return data;
}

export async function fetchModelConfigChain(
  projectId: string,
  modelId: string,
  sqlPath?: string,
): Promise<ConfigChainResponse> {
  const { data } = await apiClient.get<ConfigChainResponse>(`/projects/${projectId}/models/${modelId}/config-chain`, {
    params: sqlPath ? { sql_path: sqlPath } : undefined,
  });
  return data;
}

export async function fetchBuildPreview(
  projectId: string,
  engine: string,
  payload: {
    model_id: string;
    sql_path: string;
    inline_sql?: string;
  },
): Promise<BuildPreviewResponse> {
  const { data } = await apiClient.post<BuildPreviewResponse>(`/projects/${projectId}/build/${engine}/preview`, payload);
  return data;
}

export async function runProjectBuild(
  projectId: string,
  payload: {
    model_id?: string;
    engine: "dqcr" | "airflow" | "dbt" | "oracle_plsql";
    context: string;
    dry_run?: boolean;
    output_path?: string;
  },
): Promise<BuildRunResult> {
  const { data } = await apiClient.post<BuildRunResult>(`/projects/${projectId}/build`, payload);
  return data;
}

export async function fetchBuildHistory(projectId: string): Promise<BuildRunResult[]> {
  const { data } = await apiClient.get<BuildRunResult[]>(`/projects/${projectId}/build/history`);
  return Array.isArray(data) ? data : [];
}

export async function fetchBuildFiles(projectId: string, buildId: string): Promise<BuildFilesResponse> {
  const { data } = await apiClient.get<BuildFilesResponse>(`/projects/${projectId}/build/${buildId}/files`);
  if (!isRecord(data)) {
    return {
      project_id: projectId,
      build_id: buildId,
      engine: "dqcr",
      output_path: "",
      files: [],
      tree: { name: "output", path: "", type: "directory", children: [] },
    };
  }
  return {
    project_id: typeof data.project_id === "string" ? data.project_id : projectId,
    build_id: typeof data.build_id === "string" ? data.build_id : buildId,
    engine: typeof data.engine === "string" ? data.engine : "dqcr",
    output_path: typeof data.output_path === "string" ? data.output_path : "",
    files: Array.isArray(data.files)
      ? data.files
          .filter((item) => isRecord(item) && typeof item.path === "string")
          .map((item) => ({
            path: String(item.path),
            source_path: typeof item.source_path === "string" ? item.source_path : null,
            size_bytes: typeof item.size_bytes === "number" ? item.size_bytes : 0,
          }))
      : [],
    tree: normalizeBuildFileNode(data.tree, "output", ""),
  };
}

export function getBuildDownloadUrl(projectId: string, buildId: string): string {
  return `/api/v1/projects/${projectId}/build/${buildId}/download`;
}

export function getBuildFileDownloadUrl(projectId: string, buildId: string, path: string): string {
  const params = new URLSearchParams({ path });
  return `/api/v1/projects/${projectId}/build/${buildId}/download?${params.toString()}`;
}

export async function fetchBuildFileContent(projectId: string, buildId: string, path: string): Promise<string> {
  const { data } = await apiClient.get<BuildFileContentResponse>(`/projects/${projectId}/build/${buildId}/files/content`, {
    params: { path },
  });
  return data.content;
}

export async function listAdminTemplates(): Promise<Array<{ name: string }>> {
  const { data } = await apiClient.get<Array<{ name: string }>>("/admin/templates");
  return data;
}

export async function fetchAdminTemplate(name: string): Promise<AdminTemplateResponse> {
  const { data } = await apiClient.get<AdminTemplateResponse>(`/admin/templates/${name}`);
  return data;
}

export async function saveAdminTemplate(
  name: string,
  payload: { content: string; rules: { folders: AdminTemplateFolderRule[] } },
): Promise<AdminTemplateResponse> {
  const { data } = await apiClient.put<AdminTemplateResponse>(`/admin/templates/${name}`, payload);
  return data;
}

export async function fetchAdminRules(): Promise<AdminRuleItem[]> {
  const { data } = await apiClient.get<{ rules: AdminRuleItem[] }>("/admin/rules");
  return data.rules;
}

export async function saveAdminRules(rules: AdminRuleItem[]): Promise<AdminRuleItem[]> {
  const { data } = await apiClient.put<{ rules: AdminRuleItem[] }>("/admin/rules", { rules });
  return data.rules;
}

export async function fetchAdminMacros(): Promise<AdminMacroItem[]> {
  const { data } = await apiClient.get<{ macros: AdminMacroItem[] }>("/admin/macros");
  return data.macros;
}

export async function runProjectValidation(
  projectId: string,
  payload?: {
    model_id?: string;
    categories?: string[];
  },
): Promise<ValidationRunResult> {
  const { data } = await apiClient.post<ValidationRunResult>(`/projects/${projectId}/validate`, payload ?? {});
  return data;
}

export async function fetchValidationHistory(projectId: string): Promise<ValidationRunResult[]> {
  const { data } = await apiClient.get<ValidationRunResult[]>(`/projects/${projectId}/validate/history`);
  return data;
}

export async function applyValidationQuickFix(
  projectId: string,
  payload: {
    type: "add_field" | "rename_folder";
    model_id?: string;
    file_path?: string;
    field_name?: string;
    new_name?: string;
    rerun?: boolean;
  },
): Promise<ValidationQuickFixResponse> {
  const { data } = await apiClient.post<ValidationQuickFixResponse>(`/projects/${projectId}/validate/quickfix`, payload);
  return data;
}

export async function getDryRunQuickFix(
  projectId: string,
  payload: { type: "add_field" | "rename_folder"; model_id: string; field_name?: string; file_path?: string; new_name?: string },
): Promise<ValidationQuickFixDryRunResponse> {
  const { data } = await apiClient.post<ValidationQuickFixDryRunResponse>(`/projects/${projectId}/validate/quickfix`, {
    ...payload,
    dry_run: true,
    rerun: false,
  });
  return data;
}

export async function fetchModelYmlSchema(): Promise<ModelYmlSchemaResponse> {
  const { data } = await apiClient.get<ModelYmlSchemaResponse>("/projects/schema/model-yml");
  return data;
}

export async function fetchProjectParameters(projectId: string): Promise<ProjectParameterItem[]> {
  const { data } = await apiClient.get<ProjectParameterItem[]>(`/projects/${projectId}/parameters`);
  return data;
}

export async function createProjectParameter(
  projectId: string,
  payload: {
    name: string;
    scope: string;
    description: string;
    domain_type: string;
    values: Record<string, ProjectParameterValueItem>;
  },
): Promise<ProjectParameterItem> {
  const { data } = await apiClient.post<ProjectParameterItem>(`/projects/${projectId}/parameters`, payload);
  return data;
}

export async function updateProjectParameter(
  projectId: string,
  parameterId: string,
  payload: {
    name?: string;
    scope?: string;
    description?: string;
    domain_type?: string;
    values?: Record<string, ProjectParameterValueItem>;
  },
  scope?: string,
): Promise<ProjectParameterItem> {
  const { data } = await apiClient.put<ProjectParameterItem>(`/projects/${projectId}/parameters/${parameterId}`, payload, {
    params: scope ? { scope } : undefined,
  });
  return data;
}

export async function deleteProjectParameter(projectId: string, parameterId: string, scope?: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/parameters/${parameterId}`, {
    params: scope ? { scope } : undefined,
  });
}

export async function testProjectParameter(
  projectId: string,
  parameterId: string,
  payload: {
    context?: string;
  },
  scope?: string,
): Promise<ProjectParameterTestResponse> {
  const { data } = await apiClient.post<ProjectParameterTestResponse>(`/projects/${projectId}/parameters/${parameterId}/test`, payload, {
    params: scope ? { scope } : undefined,
  });
  return data;
}

export async function fetchModelObject(projectId: string, modelId: string): Promise<ModelObjectResponse> {
  const { data } = await apiClient.get<ModelObjectResponse>(`/projects/${projectId}/models/${modelId}`);
  return data;
}

export async function saveModelObject(
  projectId: string,
  modelId: string,
  payload: { model: ModelObjectResponse["model"] },
): Promise<{ project_id: string; model_id: string; path: string; saved: boolean }> {
  const { data } = await apiClient.put<{ project_id: string; model_id: string; path: string; saved: boolean }>(
    `/projects/${projectId}/models/${modelId}`,
    payload,
  );
  return data;
}
