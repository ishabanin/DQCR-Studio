export function GraphLegend() {
  const items = [
    { color: "#1D9E75", label: "active" },
    { color: "var(--color-border-secondary)", label: "dependency" },
    { color: "#EF9F27", label: "fallback / stale" },
    { color: "#E24B4A", label: "error" },
  ];

  return (
    <div className="lg-legend">
      {items.map((item) => (
        <div key={item.label} className="lg-leg-row">
          <div className="lg-leg-line" style={{ background: item.color }} />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
