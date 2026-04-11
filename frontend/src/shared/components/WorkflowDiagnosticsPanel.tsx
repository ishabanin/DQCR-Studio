import { WorkflowDiagnostics, WorkflowStatus } from "../../api/projects";

function statusLabel(status: WorkflowStatus | null): string {
  if (status === "ready") return "ready";
  if (status === "stale") return "stale";
  if (status === "building") return "building";
  if (status === "error") return "error";
  return "missing";
}

function statusHint(status: WorkflowStatus | null, source: "framework_cli" | "fallback" | null): string {
  if (status === "ready") return source === "fallback" ? "Ready, but served from fallback payload." : "Workflow cache is healthy.";
  if (status === "stale") return "Workflow cache is stale. UI may show outdated execution details.";
  if (status === "building") return "Workflow cache is rebuilding. Details may be incomplete until build finishes.";
  if (status === "error") return "Workflow build failed. IDE is running in degraded mode.";
  return "Workflow cache is missing. Build the workflow to enable execution-aware features.";
}

function issueAdvice(code: string): string {
  if (code === "workflow_missing") return "Run workflow rebuild for the model.";
  if (code === "workflow_building") return "Wait for build completion or refresh in a few seconds.";
  if (code === "stale_payload") return "Rebuild workflow to refresh stale payload.";
  if (code === "workflow_error") return "Check FW build logs and fix validation/build issues.";
  if (code === "fallback_source") return "Backend uses fallback data. Rebuild to restore framework payload.";
  if (code === "legacy_payload") return "Payload was normalized from legacy shape. Rebuild to produce native v1 metadata.";
  if (code === "missing_heavy_fields") return "Open step details cautiously: some SQL artifacts are unavailable.";
  if (code === "contract_gaps") return "Contract fields are incomplete; execution UI may hide/approximate some relations.";
  return "Review workflow payload and rebuild if this issue persists.";
}

export function WorkflowDiagnosticsPanel({
  modelId,
  status,
  source,
  diagnostics,
  updatedAt,
}: {
  modelId: string;
  status: WorkflowStatus | null;
  source: "framework_cli" | "fallback" | null;
  diagnostics?: WorkflowDiagnostics;
  updatedAt?: string | null;
}) {
  const issueItems = diagnostics?.issues ?? [];
  const hasDegradation = status !== "ready" || issueItems.length > 0 || source === "fallback";
  if (!hasDegradation) return null;

  return (
    <section className="wfdiag-panel">
      <div className="wfdiag-head">
        <strong>Workflow Diagnostics · {modelId}</strong>
        <span className={`wfdiag-pill wfdiag-pill-${statusLabel(status)}`}>{statusLabel(status)}</span>
      </div>
      <p className="wfdiag-note">
        {statusHint(status, source)} Source: {source ?? "unknown"}
        {updatedAt ? ` · Updated: ${new Date(updatedAt).toLocaleString()}` : ""}
      </p>
      {issueItems.length > 0 ? (
        <ul className="wfdiag-list">
          {issueItems.map((item) => (
            <li key={`${item.code}-${item.message}`}>
              <span className="wfdiag-code">{item.code}</span>
              <span>{item.message}</span>
              <span className="wfdiag-advice">{issueAdvice(item.code)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {diagnostics ? (
        <p className="wfdiag-coverage">
          Coverage: steps {diagnostics.coverage.steps_total}, sql metadata {diagnostics.coverage.sql_steps_with_metadata}/
          {diagnostics.coverage.sql_steps_total}, heavy SQL {diagnostics.coverage.sql_steps_with_source_sql}/
          {diagnostics.coverage.sql_steps_total}
        </p>
      ) : null}
    </section>
  );
}
