import type { ContextItem } from "../../../api/projects";

export function ContextsCard({ contexts }: { contexts: ContextItem[] }) {
  return (
    <section className="project-card">
      <div className="project-card-head">
        <div>
          <p className="project-card-eyebrow">Contexts</p>
          <h2>Execution environments</h2>
        </div>
        <span className="project-status-pill">{contexts.length}</span>
      </div>

      {contexts.length === 0 ? (
        <p className="project-muted-copy">No contexts available.</p>
      ) : (
        <div className="project-chip-list">
          {contexts.map((context) => (
            <span key={context.id} className="project-chip">
              <strong>{context.name}</strong>
              <span>{context.id}</span>
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
