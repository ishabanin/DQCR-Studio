export function MetricCard({ value, label }: { value: number; label: string }) {
  return (
    <div className="hub-metric-card">
      <div className="hub-metric-value">{value}</div>
      <div style={{ fontSize: "var(--hub-text-xs)", color: "var(--color-text-secondary)" }}>{label}</div>
    </div>
  );
}
