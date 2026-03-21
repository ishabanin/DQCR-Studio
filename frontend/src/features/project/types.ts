export interface ProjectSettings {
  name: string;
  description: string;
  template: string;
  version: string;
  owner: string;
}

export interface PropertyEntry {
  id: string;
  key: string;
  value: string;
}

export interface ModelSummary {
  id: string;
  folderCount: number;
  sqlCount: number;
  paramCount: number;
  targetTable: string | null;
  template: string | null;
}

export type ModelCacheStatus = "ready" | "stale" | "building" | "error" | "missing";

export interface ContextInfo {
  name: string;
  tools: string[];
  constants: Record<string, string | number | boolean>;
  flags: Record<string, boolean>;
}

export interface ParamInfo {
  id: string;
  name: string;
  domain_type: string;
  scope: "global" | string;
  values: Record<string, { type: "static" | "dynamic"; value: string }>;
}

export interface ProjectInfoData {
  settings: ProjectSettings;
  properties: PropertyEntry[];
  models: ModelSummary[];
  cacheStatuses: Record<string, ModelCacheStatus>;
  totalFolders: number;
  totalSqlFiles: number;
  totalContexts: number;
  contexts: ContextInfo[];
  globalParams: ParamInfo[];
  modelScopedCount: number;
  projectYml: string;
}
