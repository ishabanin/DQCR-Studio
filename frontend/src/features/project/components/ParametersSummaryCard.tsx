import type { ProjectParameterItem } from "../../../api/projects";
import type { ModelSummary } from "../hooks/useProjectInfo";

function byScope(parameters: ProjectParameterItem[], prefix: string) {
  return parameters.filter((item) => item.scope.startsWith(prefix));
}

export function ParametersSummaryCard({
  parameters,
  models,
}: {
  parameters: ProjectParameterItem[];
  models: ModelSummary[];
}) {
  const globalParams = parameters.filter((item) => item.scope === "global");
  const modelParams = byScope(parameters, "model:");
  const dynamicParams = parameters.filter((item) => Object.values(item.values ?? {}).some((value) => value.type === "dynamic"));
  const paramFiles = models.reduce((sum, item) => sum + item.paramCount, 0);

  return (
    <section className="project-card">
      <div className="project-card-head">
        <div>
          <p className="project-card-eyebrow">Parameters</p>
          <h2>Configuration surface</h2>
        </div>
        <span className="project-status-pill">{parameters.length} API items</span>
      </div>

      <div className="project-mini-stats">
        <div className="project-mini-stat">
          <strong>{globalParams.length}</strong>
          <span>global</span>
        </div>
        <div className="project-mini-stat">
          <strong>{modelParams.length}</strong>
          <span>model-scoped</span>
        </div>
        <div className="project-mini-stat">
          <strong>{dynamicParams.length}</strong>
          <span>dynamic</span>
        </div>
        <div className="project-mini-stat">
          <strong>{paramFiles}</strong>
          <span>param files</span>
        </div>
      </div>

      <p className="project-muted-copy">
        API parameters and model parameter files are shown together so the page reflects both runtime config and on-disk structure.
      </p>
    </section>
  );
}
