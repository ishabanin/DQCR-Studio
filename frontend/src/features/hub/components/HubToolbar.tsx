import type { FilterState } from "../types";

interface HubToolbarProps {
  filters: FilterState;
  onFilter: (patch: Partial<FilterState>) => void;
  view: "grid" | "list";
  setView: (value: "grid" | "list") => void;
}

function SearchInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ position: "relative", flex: 1, maxWidth: 280 }}>
      <span
        style={{
          position: "absolute",
          left: 9,
          top: "50%",
          transform: "translateY(-50%)",
          fontSize: 12,
          color: "var(--color-text-tertiary)",
          pointerEvents: "none",
        }}
      >
        ⌕
      </span>
      <input
        className="hub-input hub-focus-ring"
        style={{ paddingLeft: 28 }}
        placeholder="Search projects…"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {value && (
        <button
          style={{
            position: "absolute",
            right: 8,
            top: "50%",
            transform: "translateY(-50%)",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 12,
            color: "var(--color-text-tertiary)",
            padding: "2px 4px",
          }}
          onClick={() => onChange("")}
        >
          ✕
        </button>
      )}
    </div>
  );
}

function PillFilter({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "5px 12px",
        borderRadius: 20,
        border: "0.5px solid",
        borderColor: active ? "var(--hub-accent-200)" : "var(--color-border-secondary)",
        background: active ? "var(--hub-accent-50)" : "var(--hub-surface-card)",
        color: active ? "var(--hub-accent-600)" : "var(--color-text-secondary)",
        fontSize: "var(--hub-text-sm)",
        fontFamily: "var(--hub-font-ui)",
        cursor: "pointer",
        fontWeight: active ? "var(--hub-weight-medium)" : "var(--hub-weight-regular)",
        transition: "all var(--hub-transition-fast)",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}

function ViewToggle({ value, onChange }: { value: "grid" | "list"; onChange: (v: "grid" | "list") => void }) {
  return (
    <div
      style={{
        display: "flex",
        border: "var(--hub-border-medium)",
        borderRadius: 6,
        overflow: "hidden",
      }}
    >
      {(["grid", "list"] as const).map((variant) => (
        <button
          key={variant}
          onClick={() => onChange(variant)}
          style={{
            padding: "5px 11px",
            background: value === variant ? "var(--hub-surface-panel)" : "var(--hub-surface-card)",
            border: "none",
            color: value === variant ? "var(--color-text-primary)" : "var(--color-text-secondary)",
            cursor: "pointer",
            fontSize: 14,
            fontFamily: "var(--hub-font-ui)",
            transition: "background var(--hub-transition-fast)",
          }}
        >
          {variant === "grid" ? "⊞" : "≡"}
        </button>
      ))}
    </div>
  );
}

export function HubToolbar({ filters, onFilter, view, setView }: HubToolbarProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
      <SearchInput value={filters.search} onChange={(value) => onFilter({ search: value })} />
      <PillFilter
        label="◎ Public"
        active={filters.visibility === "public"}
        onClick={() => onFilter({ visibility: filters.visibility === "public" ? null : "public" })}
      />
      <PillFilter
        label="◉ Private"
        active={filters.visibility === "private"}
        onClick={() => onFilter({ visibility: filters.visibility === "private" ? null : "private" })}
      />
      <div style={{ flex: 1 }} />
      <ViewToggle value={view} onChange={setView} />
    </div>
  );
}
