import type { ModelSummary } from "../hooks/useProjectInfo";
import { ModelCard } from "./ModelCard";

export function ModelSummaryGrid({ models }: { models: ModelSummary[] }) {
  return (
    <section className="project-card">
      <div className="project-card-head">
        <div>
          <p className="project-card-eyebrow">Models</p>
          <h2>Workflow overview</h2>
        </div>
        <span className="project-status-pill">{models.length} total</span>
      </div>

      {models.length === 0 ? (
        <p className="project-muted-copy">No models found in the project tree.</p>
      ) : (
        <div className="project-models-grid">
          {models.map((model) => (
            <ModelCard key={model.id} model={model} />
          ))}
        </div>
      )}
    </section>
  );
}
