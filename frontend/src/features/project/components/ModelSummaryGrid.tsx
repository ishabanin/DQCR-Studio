import { ModelCard } from "./ModelCard";
import type { ModelCacheStatus, ModelSummary } from "../types";

export function ModelSummaryGrid({
  models,
  cacheStatuses,
  totalFolders,
  totalSql,
  onOpenModel,
  onCreateModel,
}: {
  models: ModelSummary[];
  cacheStatuses: Record<string, ModelCacheStatus>;
  totalFolders: number;
  totalSql: number;
  onOpenModel: (modelId: string) => void;
  onCreateModel?: () => void;
}) {
  return (
    <div style={{ marginBottom: "var(--pi-gap-lg)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "var(--pi-gap-md)",
        }}
      >
        <span style={{ fontSize: "var(--pi-text-base)", fontWeight: "var(--pi-weight-medium)" }}>Models</span>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: "var(--pi-text-xs)", color: "var(--color-text-tertiary)" }}>
            {models.length} models · {totalFolders} folders · {totalSql} SQL files
          </span>
          {onCreateModel ? (
            <button className="pi-btn-secondary" style={{ padding: "5px 10px", fontSize: 11 }} onClick={onCreateModel}>
              New model
            </button>
          ) : null}
        </div>
      </div>

      {models.length === 0 ? (
        <div className="pi-empty-models">
          <div style={{ fontSize: 28, marginBottom: 10, opacity: 0.25 }}>◼</div>
          <div
            style={{
              fontSize: "var(--pi-text-base)",
              fontWeight: "var(--pi-weight-medium)",
              marginBottom: 6,
              color: "var(--color-text-secondary)",
            }}
          >
            No models yet
          </div>
          <div
            style={{
              fontSize: "var(--pi-text-sm)",
              color: "var(--color-text-tertiary)",
              maxWidth: 260,
              margin: "0 auto",
            }}
          >
            Create a model scaffold in <code>model/&lt;ModelId&gt;/model.yml</code> to get started
          </div>
          {onCreateModel ? (
            <button className="pi-btn-primary visible" style={{ marginTop: 14, padding: "7px 14px", fontSize: 11 }} onClick={onCreateModel}>
              Create first model
            </button>
          ) : null}
        </div>
      ) : (
        <div className="pi-models-grid">
          {models.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              cacheStatus={cacheStatuses[model.id] ?? "missing"}
              onClick={() => onOpenModel(model.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
