import { useMemo } from "react";

import type { SqlViewMode } from "../types/sqlView";

function toStringRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object") return {};
  const entries = Object.entries(value as Record<string, unknown>)
    .filter((entry): entry is [string, string] => typeof entry[0] === "string" && typeof entry[1] === "string");
  return Object.fromEntries(entries);
}

export function useSqlRenderedContent(step: unknown, mode: SqlViewMode, tool: string | null): string | null {
  return useMemo(() => {
    if (mode === "source") return null;
    if (!step || typeof step !== "object") return null;

    const sqlModel = (step as { sql_model?: unknown }).sql_model;
    if (!sqlModel || typeof sqlModel !== "object") return null;

    const preparedSql = toStringRecord((sqlModel as { prepared_sql?: unknown }).prepared_sql);
    const renderedSql = toStringRecord((sqlModel as { rendered_sql?: unknown }).rendered_sql);

    if (!tool) return null;
    if (mode === "prepared") return preparedSql[tool] ?? null;
    if (mode === "rendered") return renderedSql[tool] ?? null;
    return null;
  }, [mode, step, tool]);
}
