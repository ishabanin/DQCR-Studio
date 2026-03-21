import type { ModelCacheStatus, ModelSummary } from "../types";

const CACHE_LABEL: Record<ModelCacheStatus, string> = {
  ready: "cache ready",
  stale: "cache stale",
  building: "building…",
  error: "cache error",
  missing: "no cache",
};

function templateClass(template: string | null): string | null {
  if (!template) return null;
  if (template === "flx") return "pi-tpl-flx";
  if (template === "dwh_mart") return "pi-tpl-dwh";
  return "pi-tpl-dq";
}

export function ModelCard({
  model,
  cacheStatus,
  onClick,
}: {
  model: ModelSummary;
  cacheStatus: ModelCacheStatus;
  onClick: () => void;
}) {
  return (
    <div
      className="pi-model-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => event.key === "Enter" && onClick()}
    >
      <div
        style={{
          padding: "10px var(--pi-card-px) 8px",
          borderBottom: "var(--pi-border-subtle)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <span className="pi-link">{model.id}</span>
        <span className="pi-model-arrow">⬡ Lineage →</span>
      </div>

      <div style={{ padding: "8px var(--pi-card-px)", display: "flex", flexDirection: "column", gap: 4 }}>
        {[
          { color: "var(--pi-accent-400)", label: "Folders", value: model.folderCount },
          { color: "var(--pi-info-text)", label: "SQL files", value: model.sqlCount },
          { color: "var(--pi-warning-text)", label: "Parameters", value: model.paramCount },
        ].map((row) => (
          <div
            key={row.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: "var(--pi-text-xs)",
              color: "var(--color-text-secondary)",
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: row.color,
                flexShrink: 0,
              }}
            />
            <span style={{ flex: 1 }}>{row.label}</span>
            <span
              style={{
                fontWeight: "var(--pi-weight-medium)",
                color: "var(--color-text-primary)",
                fontFamily: "var(--pi-font-mono)",
                fontSize: "var(--pi-text-xs)",
              }}
            >
              {row.value}
            </span>
          </div>
        ))}

        {model.targetTable ? (
          <div
            style={{
              marginTop: 4,
              paddingTop: 5,
              borderTop: "var(--pi-border-subtle)",
              fontSize: "var(--pi-text-2xs)",
              fontFamily: "var(--pi-font-mono)",
              color: "var(--color-text-tertiary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            target: {model.targetTable}
          </div>
        ) : null}
      </div>

      <div
        style={{
          padding: "6px var(--pi-card-px)",
          background: "var(--pi-bg-panel)",
          borderTop: "var(--pi-border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <div className={`pi-cache-dot pi-cache-${cacheStatus}`} />
        <span style={{ fontSize: "var(--pi-text-2xs)", color: "var(--color-text-tertiary)", flex: 1 }}>{CACHE_LABEL[cacheStatus]}</span>
        {model.template ? <span className={`pi-tpl-badge ${templateClass(model.template)}`}>{model.template}</span> : null}
      </div>
    </div>
  );
}
