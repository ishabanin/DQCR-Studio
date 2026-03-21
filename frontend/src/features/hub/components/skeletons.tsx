export function ProjectCardSkeleton() {
  return (
    <div style={{ background: "var(--hub-surface-card)", border: "var(--hub-border-subtle)", borderRadius: "var(--hub-radius-card)", overflow: "hidden" }}>
      <div style={{ padding: "12px 14px 10px", borderBottom: "var(--hub-border-subtle)" }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <div className="hub-skeleton" style={{ width: 32, height: 32, borderRadius: 7 }} />
          <div style={{ flex: 1 }}>
            <div className="hub-skeleton" style={{ height: 14, width: "65%", marginBottom: 6 }} />
            <div style={{ display: "flex", gap: 4 }}>
              <div className="hub-skeleton" style={{ height: 18, width: 60, borderRadius: 20 }} />
              <div className="hub-skeleton" style={{ height: 18, width: 52, borderRadius: 20 }} />
            </div>
          </div>
        </div>
        <div className="hub-skeleton" style={{ height: 11, width: "80%", marginBottom: 5 }} />
        <div className="hub-skeleton" style={{ height: 11, width: "55%", marginBottom: 8 }} />
      </div>
      <div style={{ padding: "8px 14px", display: "flex", gap: 14 }}>
        {[56, 48, 40].map((w) => (
          <div key={w} className="hub-skeleton" style={{ height: 11, width: w }} />
        ))}
      </div>
      <div style={{ padding: "7px 14px", background: "var(--hub-surface-panel)", borderTop: "var(--hub-border-subtle)", display: "flex", gap: 8 }}>
        <div className="hub-skeleton" style={{ width: 7, height: 7, borderRadius: "50%", flexShrink: 0 }} />
        <div className="hub-skeleton" style={{ height: 11, flex: 1 }} />
        <div className="hub-skeleton" style={{ height: 11, width: 60 }} />
      </div>
    </div>
  );
}

export function StatsRowSkeleton() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 20 }}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} style={{ background: "var(--hub-surface-panel)", borderRadius: "var(--border-radius-md)", padding: "12px 14px" }}>
          <div className="hub-skeleton" style={{ height: 28, width: 48, marginBottom: 8 }} />
          <div className="hub-skeleton" style={{ height: 12, width: 80 }} />
        </div>
      ))}
    </div>
  );
}
