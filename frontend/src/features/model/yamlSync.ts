import type { ModelObjectResponse } from "../../api/projects";

export type SyncStatus = "synced" | "syncing" | "conflict";

export function normalizeYamlText(value: string): string {
  return value.replace(/\r\n/g, "\n").trimEnd() + "\n";
}

export function areModelsEqual(
  left: ModelObjectResponse["model"] | null,
  right: ModelObjectResponse["model"] | null,
): boolean {
  if (!left || !right) return false;
  return JSON.stringify(left) === JSON.stringify(right);
}

export function resolveYamlSyncStatus(hasError: boolean): SyncStatus {
  return hasError ? "conflict" : "synced";
}

