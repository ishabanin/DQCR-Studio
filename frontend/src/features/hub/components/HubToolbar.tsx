import type { FilterState } from "../types";

interface HubToolbarProps {
  filters: FilterState;
  onFilter: (patch: Partial<FilterState>) => void;
  view: "grid" | "list";
  setView: (value: "grid" | "list") => void;
  onOpenCatalog: () => void;
}

function SearchInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ position: "relative", flex: 1, maxWidth: 320 }}>
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
      className={active ? "hub-toolbar-pill active" : "hub-toolbar-pill"}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function ViewToggle({ value, onChange }: { value: "grid" | "list"; onChange: (v: "grid" | "list") => void }) {
  return (
    <div className="hub-view-toggle">
      {(["grid", "list"] as const).map((variant) => (
        <button
          key={variant}
          onClick={() => onChange(variant)}
          className={value === variant ? "hub-view-btn active" : "hub-view-btn"}
        >
          {variant === "grid" ? "⊞" : "≡"}
        </button>
      ))}
    </div>
  );
}

export function HubToolbar({ filters, onFilter, view, setView, onOpenCatalog }: HubToolbarProps) {
  return (
    <div className="hub-toolbar">
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
      <button className="hub-btn-secondary" onClick={onOpenCatalog}>
        Data Catalog
      </button>
      <div className="hub-toolbar-spacer" />
      <ViewToggle value={view} onChange={setView} />
    </div>
  );
}
