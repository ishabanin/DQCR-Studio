import { useEditorStore } from "../../../app/store/editorStore";
import type { ParamInfo } from "../types";

function formatContextSummary(param: ParamInfo): string {
  const values = param.values ?? {};
  const keys = Object.keys(values);

  if (keys.length === 0) return "—";

  const hasDynamic = Object.values(values).some((item) => item.type === "dynamic");
  const hasStatic = Object.values(values).some((item) => item.type === "static");

  if (keys.length === 1 && keys[0] === "all") {
    return "static · all";
  }

  if (hasDynamic && hasStatic) {
    const dynamicContexts = keys.filter((key) => values[key]?.type === "dynamic").join(", ");
    return `static / ${dynamicContexts}: dynamic`;
  }

  if (hasDynamic) return `dynamic · ${keys.join(", ")}`;
  return `static · ${keys.join(", ")}`;
}

export function ParametersSummaryCard({
  globalParams,
  modelScopedCount,
}: {
  globalParams: ParamInfo[];
  modelScopedCount: number;
}) {
  const setActiveTab = useEditorStore((state) => state.setActiveTab);

  return (
    <div className="pi-card">
      <div className="pi-card-header">
        <span className="pi-card-title">Global parameters</span>
        <button className="pi-card-action" onClick={() => setActiveTab("parameters")}>
          View all →
        </button>
      </div>

      {globalParams.map((param) => (
        <div key={param.id} className="pi-param-item">
          <span className="pi-param-name">{param.name}</span>
          <span className="pi-param-type">{param.domain_type || "string"}</span>
          <span style={{ fontSize: "var(--pi-text-2xs)", color: "var(--color-text-tertiary)" }}>global</span>
          <span className="pi-param-ctx">{formatContextSummary(param)}</span>
        </div>
      ))}

      {modelScopedCount > 0 ? (
        <div
          style={{
            padding: "8px var(--pi-card-px)",
            fontSize: "var(--pi-text-xs)",
            color: "var(--color-text-tertiary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: "var(--pi-border-subtle)",
          }}
        >
          <span>+ {modelScopedCount} model-scoped parameters</span>
          <button
            className="pi-card-action"
            style={{ fontSize: "var(--pi-text-xs)" }}
            onClick={() => setActiveTab("parameters")}
          >
            View →
          </button>
        </div>
      ) : null}
    </div>
  );
}
