export type RouteTarget =
  | { tab: "sql"; filePath: string; line?: number }
  | { tab: "model"; modelId: string }
  | { tab: "parameters"; paramId?: string; scope?: string }
  | { tab: "lineage" };

export function routeValidationError(
  filePath: string | null | undefined,
  line: number | null | undefined,
): RouteTarget {
  if (!filePath) return { tab: "lineage" };

  if (filePath.endsWith("model.yml")) {
    const match = filePath.match(/model\/([^/]+)\/model\.yml/);
    const modelId = match?.[1] ?? "";
    return { tab: "model", modelId };
  }

  if (filePath.includes("/parameters/") && filePath.endsWith(".yml")) {
    const match = filePath.match(/parameters\/([^/]+)\.yml/);
    const paramId = match?.[1];
    const scope = filePath.includes("model/") ? "model" : "global";
    return { tab: "parameters", paramId, scope };
  }

  if (filePath.includes("/contexts/") && filePath.endsWith(".yml")) {
    return { tab: "lineage" };
  }

  if (filePath.endsWith("folder.yml")) {
    return { tab: "sql", filePath, line: line ?? undefined };
  }

  if (filePath.endsWith(".sql")) {
    return { tab: "sql", filePath, line: line ?? undefined };
  }

  return { tab: "sql", filePath, line: line ?? undefined };
}

export function getRouteLabel(filePath: string | null | undefined, line: number | null | undefined): string {
  const route = routeValidationError(filePath, line);
  switch (route.tab) {
    case "sql":
      return "→ SQL editor";
    case "model":
      return "→ Model editor";
    case "parameters":
      return "→ Parameters";
    case "lineage":
      return "→ Lineage";
  }
}
