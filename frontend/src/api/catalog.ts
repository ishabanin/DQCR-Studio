import { apiClient } from "./client";

export interface CatalogMeta {
  source_filename: string;
  loaded_at: string;
  entity_count: number;
  attribute_count: number;
  version_label: string;
}

export interface CatalogStatus {
  available: boolean;
  meta: CatalogMeta | null;
}

export interface EntitySummary {
  name: string;
  display_name: string;
  module: string;
  attribute_count: number;
}

export interface EntitySearchResult {
  entities: EntitySummary[];
  total: number;
}

export interface CatalogAttribute {
  name: string;
  display_name: string;
  description: string;
  domain_type: string;
  raw_type: string;
  is_nullable: boolean;
  is_key: boolean;
  position: number;
}

export interface CatalogEntity extends EntitySummary {
  info_object: string;
  attributes: CatalogAttribute[];
}

export async function getCatalogStatus(): Promise<CatalogStatus> {
  const { data } = await apiClient.get<CatalogStatus>("/catalog");
  return {
    available: Boolean(data?.available),
    meta: data?.meta ?? null,
  };
}

export async function uploadCatalog(file: File, versionLabel: string): Promise<CatalogStatus> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("version_label", versionLabel);

  const { data } = await apiClient.post<CatalogStatus>("/catalog/upload", formData, {
    timeout: 180000,
  });
  return {
    available: Boolean(data?.available),
    meta: data?.meta ?? null,
  };
}

export async function searchEntities(query: string, limit = 20): Promise<EntitySearchResult> {
  const { data } = await apiClient.get<EntitySearchResult>("/catalog/entities", {
    params: {
      search: query,
      limit,
    },
  });

  return {
    entities: Array.isArray(data?.entities) ? data.entities : [],
    total: typeof data?.total === "number" ? data.total : 0,
  };
}

export async function getEntity(name: string): Promise<CatalogEntity> {
  const { data } = await apiClient.get<CatalogEntity>(`/catalog/entities/${encodeURIComponent(name)}`);
  return data;
}
