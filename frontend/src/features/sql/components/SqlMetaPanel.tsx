import { useMemo, useState } from "react";
import type { ReactNode } from "react";

interface SqlMetaPanelProps {
  filePath: string | null;
  modelId: string | null;
  allProjectFiles: string[];
  step: Record<string, unknown> | null;
  workflow: Record<string, unknown> | null;
  status: "ok" | "no-cache" | "not-found";
  workflowStatus: string;
  isLoading: boolean;
  onOpenFile: (path: string) => void;
  onOpenLineage: (dependency: string) => void;
}

interface AccordionSectionProps {
  sectionId: string;
  title: string;
  count?: number;
  defaultExpanded: boolean;
  children: ReactNode;
}

function useAccordionState(sectionId: string, defaultExpanded: boolean): [boolean, () => void] {
  const key = `dqcr_sql_meta_accordion_${sectionId}`;
  const [expanded, setExpanded] = useState<boolean>(() => {
    const saved = window.localStorage.getItem(key);
    if (saved === "1") return true;
    if (saved === "0") return false;
    return defaultExpanded;
  });

  const toggle = () => {
    setExpanded((current) => {
      const next = !current;
      window.localStorage.setItem(key, next ? "1" : "0");
      return next;
    });
  };

  return [expanded, toggle];
}

function AccordionSection({ sectionId, title, count, defaultExpanded, children }: AccordionSectionProps) {
  const [expanded, toggle] = useAccordionState(sectionId, defaultExpanded);
  return (
    <section className="sql-meta-section">
      <button type="button" className="sql-meta-section-trigger" onClick={toggle}>
        <span>{title}</span>
        <span className="sql-meta-section-badges">
          {typeof count === "number" ? <span className="sql-meta-count">{count}</span> : null}
          <span className={expanded ? "sql-meta-chevron sql-meta-chevron-open" : "sql-meta-chevron"}>▾</span>
        </span>
      </button>
      {expanded ? <div className="sql-meta-section-content">{children}</div> : null}
    </section>
  );
}

function getSqlMeta(step: Record<string, unknown> | null): {
  parameters: string[];
  tables: Array<{ name: string; alias: string | null; isVariable: boolean; isCte: boolean }>;
  dependencies: string[];
  folderName: string | null;
  queryName: string | null;
} {
  if (!step) {
    return { parameters: [], tables: [], dependencies: [], folderName: null, queryName: null };
  }

  const sqlModel = step.sql_model as Record<string, unknown> | undefined;
  const metadata = (sqlModel?.metadata ?? null) as Record<string, unknown> | null;

  const parameters = Array.isArray(metadata?.parameters)
    ? metadata?.parameters.filter((item): item is string => typeof item === "string")
    : [];
  const dependencies = Array.isArray(step.dependencies)
    ? step.dependencies.filter((item): item is string => typeof item === "string")
    : [];

  const tablesRaw = (metadata?.tables ?? null) as Record<string, unknown> | null;
  const tables = Object.entries(tablesRaw ?? {}).map(([name, rawValue]) => {
    const tableMeta = (rawValue ?? {}) as Record<string, unknown>;
    return {
      name,
      alias: typeof tableMeta.alias === "string" ? tableMeta.alias : null,
      isVariable: Boolean(tableMeta.is_variable),
      isCte: Boolean(tableMeta.is_cte),
    };
  });

  const fullName = typeof step.full_name === "string" ? step.full_name : "";
  const parts = fullName.split("/").filter(Boolean);
  const folderName = parts[0] ?? null;
  const queryName = parts[1] ?? null;

  return { parameters, tables, dependencies, folderName, queryName };
}

function getStepAttributes(workflow: Record<string, unknown> | null, folderName: string | null, queryName: string | null) {
  if (!workflow || !folderName || !queryName) return [];
  const config = (workflow.config ?? null) as Record<string, unknown> | null;
  const folders = (config?.folders ?? null) as Record<string, unknown> | null;
  const folderConfig = (folders?.[folderName] ?? null) as Record<string, unknown> | null;
  const queries = (folderConfig?.queries ?? null) as Record<string, unknown> | null;
  const queryConfig = (queries?.[queryName] ?? null) as Record<string, unknown> | null;
  const attributes = queryConfig?.attributes;
  if (!Array.isArray(attributes)) return [];
  return attributes.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
}

function resolveParameterFilePath(parameter: string, modelId: string | null, filesSet: Set<string>): string | null {
  const normalized = parameter.replace(/^\{\{|\}\}$/g, "").trim().split(".").pop() ?? parameter;
  const globalPath = `parameters/${normalized}.yml`;
  if (filesSet.has(globalPath)) return globalPath;
  const globalYaml = `parameters/${normalized}.yaml`;
  if (filesSet.has(globalYaml)) return globalYaml;
  if (!modelId) return null;
  const modelScopedPath = `model/${modelId}/parameters/${normalized}.yml`;
  if (filesSet.has(modelScopedPath)) return modelScopedPath;
  const modelScopedYaml = `model/${modelId}/parameters/${normalized}.yaml`;
  if (filesSet.has(modelScopedYaml)) return modelScopedYaml;
  return null;
}

export default function SqlMetaPanel({
  filePath,
  modelId,
  allProjectFiles,
  step,
  workflow,
  status,
  workflowStatus,
  isLoading,
  onOpenFile,
  onOpenLineage,
}: SqlMetaPanelProps) {
  const filesSet = useMemo(() => new Set(allProjectFiles), [allProjectFiles]);
  const { parameters, tables, dependencies, folderName, queryName } = useMemo(() => getSqlMeta(step), [step]);
  const attributes = useMemo(() => getStepAttributes(workflow, folderName, queryName), [folderName, queryName, workflow]);

  const targetTable = useMemo(() => {
    const targetRaw = (workflow?.target_table ?? null) as Record<string, unknown> | null;
    if (!targetRaw) return null;
    const schema = typeof targetRaw.schema === "string" ? targetRaw.schema : null;
    const name = typeof targetRaw.name === "string" ? targetRaw.name : typeof targetRaw.table === "string" ? targetRaw.table : null;
    if (!schema && !name) return null;
    return [schema, name].filter(Boolean).join(".");
  }, [workflow]);

  if (!filePath) {
    return (
      <aside className="sql-meta-panel">
        <p className="sql-meta-placeholder">Выберите SQL-файл</p>
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="sql-meta-panel">
        <div className="sql-meta-skeleton" />
        <div className="sql-meta-skeleton" />
        <div className="sql-meta-skeleton" />
      </aside>
    );
  }

  if (status === "no-cache") {
    return (
      <aside className="sql-meta-panel">
        <p className="sql-meta-placeholder">Метаданные недоступны: workflow cache в состоянии {workflowStatus}</p>
      </aside>
    );
  }

  if (status === "not-found") {
    return (
      <aside className="sql-meta-panel">
        <p className="sql-meta-placeholder">Шаг не найден в workflow</p>
      </aside>
    );
  }

  return (
    <aside className="sql-meta-panel">
      {parameters.length > 0 ? (
        <AccordionSection sectionId="parameters" title="Parameters" count={parameters.length} defaultExpanded>
          <div className="sql-meta-chip-list">
            {parameters.map((parameter) => {
              const resolvedPath = resolveParameterFilePath(parameter, modelId, filesSet);
              return (
                <button
                  key={parameter}
                  type="button"
                  className="sql-meta-chip sql-meta-chip-param"
                  onClick={() => {
                    if (resolvedPath) onOpenFile(resolvedPath);
                  }}
                  title={resolvedPath ?? "Файл параметра не найден"}
                >
                  {`{{${parameter}}}`}
                </button>
              );
            })}
          </div>
        </AccordionSection>
      ) : null}

      {tables.length > 0 ? (
        <AccordionSection sectionId="tables" title="Tables" count={tables.length} defaultExpanded>
          <ul className="sql-meta-list">
            {tables.map((table) => (
              <li key={table.name} className="sql-meta-list-row">
                <span className="sql-meta-inline-badge">
                  {table.isCte ? "CTE" : table.isVariable ? "VAR" : "TBL"}
                </span>
                <span>{table.alias ?? "—"} → </span>
                <code>{table.name}</code>
              </li>
            ))}
          </ul>
        </AccordionSection>
      ) : null}

      {attributes.length > 0 ? (
        <AccordionSection sectionId="attributes" title="Attributes" count={attributes.length} defaultExpanded={false}>
          <div className="sql-meta-table-wrap">
            <table className="sql-meta-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Constraints</th>
                  <th>Dist</th>
                  <th>Part</th>
                </tr>
              </thead>
              <tbody>
                {attributes.map((item, index) => (
                  <tr key={`${String(item.name ?? "attr")}-${index}`}>
                    <td>{String(item.name ?? "—")}</td>
                    <td>{String(item.domain_type ?? item.type ?? "—")}</td>
                    <td>{String(item.constraints ?? "—")}</td>
                    <td>{String(item.dist ?? item.distribution ?? "—")}</td>
                    <td>{String(item.part ?? item.partition ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AccordionSection>
      ) : null}

      {dependencies.length > 0 ? (
        <AccordionSection sectionId="dependencies" title="Dependencies" count={dependencies.length} defaultExpanded>
          <div className="sql-meta-chip-list">
            {dependencies.map((dependency) => (
              <button
                key={dependency}
                type="button"
                className="sql-meta-chip"
                onClick={() => onOpenLineage(dependency)}
                title="Перейти в Линейность"
              >
                {dependency}
              </button>
            ))}
          </div>
        </AccordionSection>
      ) : null}

      {targetTable ? (
        <AccordionSection sectionId="target-table" title="Target Table" defaultExpanded>
          <p className="sql-meta-target">
            <span className="sql-meta-inline-badge">TABLE</span> <code>{targetTable}</code>
          </p>
        </AccordionSection>
      ) : null}
    </aside>
  );
}
