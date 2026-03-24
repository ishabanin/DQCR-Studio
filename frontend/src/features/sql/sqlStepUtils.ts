export interface SqlFileKey {
  folder: string;
  queryName: string;
}

export interface SqlWorkflowStepKey {
  folder: string;
  queryName: string;
}

export function parseSqlFileKey(filePath: string | null): SqlFileKey | null {
  if (!filePath) return null;
  const parts = filePath.split("/").filter(Boolean);
  const sqlIndex = parts.findIndex((part) => part.toLowerCase() === "sql");
  if (sqlIndex < 0 || sqlIndex + 1 >= parts.length) return null;

  const folderParts = parts.slice(sqlIndex + 1, -1);
  const fileName = parts[parts.length - 1] ?? "";
  if (!fileName.toLowerCase().endsWith(".sql")) return null;

  return {
    folder: folderParts.join("/"),
    queryName: fileName.replace(/\.sql$/i, ""),
  };
}

export function getStepFolder(step: Record<string, unknown>): string {
  const folder = step.folder;
  if (typeof folder === "string") return folder.replace(/\\/g, "/").trim();

  const sqlModel = step.sql_model as Record<string, unknown> | undefined;
  const path = typeof sqlModel?.path === "string" ? sqlModel.path.replace(/\\/g, "/") : "";
  const sqlIndex = path.toLowerCase().indexOf("/sql/");
  if (sqlIndex < 0) return "";
  const parts = path.slice(sqlIndex + 5).split("/").filter(Boolean);
  if (parts.length <= 1) return "";
  return parts.slice(0, -1).join("/");
}

export function getStepQueryName(step: Record<string, unknown>): string {
  const sqlModel = step.sql_model as Record<string, unknown> | undefined;
  const sqlName = typeof sqlModel?.name === "string" ? sqlModel.name.trim() : "";
  if (sqlName) return sqlName;
  if (typeof step.name === "string" && step.name.trim()) return step.name.trim();

  const fullName = typeof step.full_name === "string" ? step.full_name.trim() : "";
  if (!fullName) return "";
  const parts = fullName.split("/").filter(Boolean);
  if (parts.length === 0) return "";
  const last = parts[parts.length - 1] ?? "";
  return last.replace(/_(?:all|default|[^/]+)$/i, "");
}

export function getStepMatchScore(step: Record<string, unknown>, key: SqlFileKey, activeContext: string): number {
  if (step.step_type !== "sql") return -1;

  const sqlModel = step.sql_model as Record<string, unknown> | undefined;
  const stepFolder = getStepFolder(step);
  const stepQueryName = getStepQueryName(step);
  const stepContext = typeof step.context === "string" ? step.context.trim() : "all";
  const fullName = typeof step.full_name === "string" ? step.full_name.replace(/\\/g, "/").trim() : "";
  const expectedFullName = key.folder ? `${key.folder}/${key.queryName}` : key.queryName;
  const modelPath = typeof sqlModel?.path === "string" ? sqlModel.path.replace(/\\/g, "/").trim() : "";
  const expectedModelPathSuffix = `/SQL/${key.folder ? `${key.folder}/` : ""}${key.queryName}.sql`;

  if (stepFolder !== key.folder || stepQueryName !== key.queryName) {
    if (!fullName.includes("/cte/") && modelPath.endsWith(expectedModelPathSuffix)) {
      return stepContext === activeContext ? 90 : stepContext === "all" ? 80 : 70;
    }
    return -1;
  }

  if (!fullName.includes("/cte/")) {
    if (stepContext === activeContext) return 100;
    if (stepContext === "all") return 90;
    return 80;
  }

  if (fullName === expectedFullName) {
    return stepContext === activeContext ? 60 : stepContext === "all" ? 50 : 40;
  }

  return -1;
}
