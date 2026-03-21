import type { ContextInfo } from "../types";

export function ContextsCard({ contexts }: { contexts: ContextInfo[] }) {
  return (
    <div className="pi-card">
      <div className="pi-card-header">
        <span className="pi-card-title">Contexts</span>
        <button className="pi-card-action" onClick={() => undefined}>
          ＋ Add context
        </button>
      </div>

      {contexts.length === 0 ? (
        <div
          style={{
            padding: "14px var(--pi-card-px)",
            fontSize: "var(--pi-text-sm)",
            color: "var(--color-text-tertiary)",
            textAlign: "center",
          }}
        >
          No contexts defined — add default.yml
        </div>
      ) : (
        contexts.map((ctx) => (
          <div key={ctx.name} className="pi-ctx-item">
            <span className="pi-ctx-name">{ctx.name}</span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, flex: 1 }}>
              {ctx.tools.map((tool) => (
                <span key={tool} className="pi-chip pi-chip-tool">
                  {tool}
                </span>
              ))}

              {Object.entries(ctx.constants).map(([key, value]) => (
                <span key={key} className="pi-chip pi-chip-const">
                  {key}: {String(value)}
                </span>
              ))}

              {Object.entries(ctx.flags).map(([key, value]) => (
                <span key={key} className={`pi-chip ${value ? "pi-chip-flag-on" : "pi-chip-flag"}`}>
                  {key}: {value ? "✓" : "✗"}
                </span>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
