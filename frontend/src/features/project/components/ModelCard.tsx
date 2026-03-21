import type { ModelSummary } from "../hooks/useProjectInfo";

function labelForStatus(status: ModelSummary["cacheStatus"]) {
  switch (status) {
    case "ready":
      return "Cache ready";
    case "stale":
      return "Needs rebuild";
    case "building":
      return "Building";
    case "error":
      return "Cache error";
    default:
      return "Cache missing";
  }
}

export function ModelCard({ model }: { model: ModelSummary }) {
  return (
    <article className="project-model-card">
      <div className="project-model-card-head">
        <div>
          <p className="project-card-eyebrow">Model</p>
          <h3>{model.id}</h3>
        </div>
        <span className={`project-status-pill project-status-pill-${model.cacheStatus}`}>{labelForStatus(model.cacheStatus)}</span>
      </div>

      <div className="project-model-grid">
        <div>
          <strong>{model.folderCount}</strong>
          <span>folders</span>
        </div>
        <div>
          <strong>{model.sqlCount}</strong>
          <span>SQL files</span>
        </div>
        <div>
          <strong>{model.paramCount}</strong>
          <span>param files</span>
        </div>
      </div>

      <dl className="project-model-meta">
        <div>
          <dt>Target table</dt>
          <dd>{model.targetTable ?? "Not surfaced yet"}</dd>
        </div>
        <div>
          <dt>Template</dt>
          <dd>{model.template ?? "Inherited from project"}</dd>
        </div>
      </dl>
    </article>
  );
}
