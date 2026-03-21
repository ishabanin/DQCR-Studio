export function VisibilitySelector({
  value,
  onChange,
}: {
  value: "public" | "private";
  onChange: (value: "public" | "private") => void;
}) {
  const options = [
    {
      value: "public" as const,
      icon: "◎",
      label: "Public",
      desc: "Visible to all workspace members",
      activeStyle: { borderColor: "var(--hub-accent-400)", background: "var(--hub-accent-50)" },
    },
    {
      value: "private" as const,
      icon: "◉",
      label: "Private",
      desc: "Only you and invited members",
      activeStyle: {
        borderColor: "var(--hub-private-active-border)",
        background: "var(--hub-private-active-bg)",
      },
    },
  ] as const;

  return (
    <div style={{ display: "flex", gap: 8 }}>
      {options.map((opt) => (
        <div
          key={opt.value}
          role="radio"
          aria-checked={value === opt.value}
          tabIndex={0}
          onClick={() => onChange(opt.value)}
          onKeyDown={(event) => event.key === "Enter" && onChange(opt.value)}
          style={{
            flex: 1,
            border: "0.5px solid",
            borderColor:
              value === opt.value
                ? opt.value === "public"
                  ? "var(--hub-accent-400)"
                  : "var(--hub-private-active-border)"
                : "var(--color-border-secondary)",
            borderRadius: 8,
            padding: "10px 12px",
            cursor: "pointer",
            background: value === opt.value ? opt.activeStyle.background : "var(--hub-surface-card)",
            transition: "all var(--hub-transition-base)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
            <span style={{ fontSize: 14 }}>{opt.icon}</span>
            <span style={{ fontSize: "var(--hub-text-sm)", fontWeight: "var(--hub-weight-medium)", color: "var(--color-text-primary)" }}>
              {opt.label}
            </span>
          </div>
          <div style={{ fontSize: "var(--hub-text-xs)", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>{opt.desc}</div>
        </div>
      ))}
    </div>
  );
}
