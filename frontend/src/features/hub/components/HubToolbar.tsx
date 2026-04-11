import Badge from "../../../shared/components/ui/Badge";
import Button from "../../../shared/components/ui/Button";
import Input from "../../../shared/components/ui/Input";
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
    <div className="hub-search-wrap">
      <span className="hub-search-icon">⌕</span>
      <Input className="hub-input hub-search-input" placeholder="Search projects…" value={value} onChange={(event) => onChange(event.target.value)} />
      {value && (
        <button type="button" className="hub-search-clear" onClick={() => onChange("")}>
          ✕
        </button>
      )}
    </div>
  );
}

function PillFilter({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" aria-pressed={active} className={active ? "hub-toolbar-pill active" : "hub-toolbar-pill"} onClick={onClick}>
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
          type="button"
          onClick={() => onChange(variant)}
          aria-pressed={value === variant}
          className={value === variant ? "hub-view-btn active" : "hub-view-btn"}
        >
          {variant === "grid" ? "⊞" : "≡"}
        </button>
      ))}
    </div>
  );
}

export function HubToolbar({ filters, onFilter, view, setView, onOpenCatalog }: HubToolbarProps) {
  const activeVisibility = filters.visibility ? 1 : 0;
  return (
    <div className="hub-toolbar">
      <SearchInput value={filters.search} onChange={(value) => onFilter({ search: value })} />
      <Badge variant="secondary" className="hub-filter-badge">
        Visibility {activeVisibility > 0 ? `(${activeVisibility})` : ""}
      </Badge>
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
      <Button variant="secondary" onClick={onOpenCatalog}>
        Data Catalog
      </Button>
      <div className="hub-toolbar-spacer" />
      <ViewToggle value={view} onChange={setView} />
    </div>
  );
}
