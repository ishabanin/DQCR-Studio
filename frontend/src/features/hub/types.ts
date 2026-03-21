export interface ProjectListItem {
  project_id: string;
  name: string;
  description: string | null;
  project_type: "internal" | "imported" | "linked";
  visibility: "public" | "private";
  tags: string[];
  cache_status: "ready" | "stale" | "building" | "error" | "missing";
  model_count: number;
  folder_count: number;
  sql_count: number;
  modified_at: string;
  source_path?: string | null;
  availability_status?: "available" | "unavailable";
}

export interface FilterState {
  search: string;
  visibility: "public" | "private" | null;
  type: "internal" | "imported" | "linked" | null;
  tag: string | null;
}

export type SortKey = "name" | "modified_at" | "model_count" | "sql_count";
export type SortDir = "asc" | "desc";

export interface CreateProjectPayload {
  mode: "create" | "import";
  project_id?: string;
  name?: string;
  description?: string;
  template?: "flx" | "dwh_mart" | "dq_control";
  source_path?: string;
  visibility: "public" | "private";
  tags: string[];
  properties?: Record<string, string>;
}

export interface MetadataUpdatePayload {
  name?: string;
  description?: string;
  visibility?: "public" | "private";
  tags?: string[];
}
