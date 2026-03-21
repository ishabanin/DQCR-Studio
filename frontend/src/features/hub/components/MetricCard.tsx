export function MetricCard({ value, label }: { value: number; label: string }) {
  return (
    <div
      style={{
        background: "var(--hub-surface-panel)",
        borderRadius: "var(--border-radius-md)",
        padding: "12px 14px",
        border: "var(--hub-border-subtle)",
      }}
    >
      <div style={{ fontSize: 28, lineHeight: 1, marginBottom: 8, color: "var(--color-text-primary)", fontWeight: "var(--hub-weight-medium)" }}>{value}</div>
      <div style={{ fontSize: "var(--hub-text-xs)", color: "var(--color-text-secondary)" }}>{label}</div>
    </div>
  );
}
