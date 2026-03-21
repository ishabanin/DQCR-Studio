import type { ReactNode } from "react";
import { getTagColor } from "../utils";
import type { FilterState } from "../types";

interface HubSidebarProps {
  counts: {
    all: number;
    public: number;
    private: number;
    internal: number;
    imported: number;
    linked: number;
    byTag: Record<string, number>;
  };
  filters: FilterState;
  onFilter: (patch: Partial<FilterState>) => void;
}

function NavSection({ label }: { label: string }) {
  return (
    <div
      style={{
        fontSize: "var(--hub-text-2xs)",
        fontWeight: "var(--hub-weight-medium)",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: "var(--color-text-tertiary)",
        padding: "6px 14px 3px",
      }}
    >
      {label}
    </div>
  );
}

interface NavItemProps {
  icon: ReactNode;
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}

function NavItem({ icon, label, count, active, onClick }: NavItemProps) {
  return (
    <div
      className={`hub-nav-item ${active ? "active" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => event.key === "Enter" && onClick()}
    >
      <span style={{ fontSize: 13, flexShrink: 0, width: 14, display: "flex", alignItems: "center" }}>{icon}</span>
      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
      <span
        style={{
          fontSize: "var(--hub-text-2xs)",
          padding: "1px 5px",
          borderRadius: 8,
          background: "var(--hub-surface-panel)",
          color: "var(--color-text-tertiary)",
          flexShrink: 0,
        }}
      >
        {count}
      </span>
    </div>
  );
}

function TagDot({ tag }: { tag: string }) {
  return (
    <span
      style={{
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: getTagColor(tag),
        display: "inline-block",
        flexShrink: 0,
      }}
    />
  );
}

export function HubSidebar({ counts, filters, onFilter }: HubSidebarProps) {
  const allTags = Object.keys(counts.byTag).sort((a, b) => counts.byTag[b] - counts.byTag[a]);

  return (
    <nav
      style={{
        width: "var(--hub-sidebar-w)",
        flexShrink: 0,
        borderRight: "var(--hub-border-subtle)",
        background: "var(--hub-surface-card)",
        padding: "12px 0",
        overflowY: "auto",
        overflowX: "hidden",
      }}
    >
      <NavSection label="Workspace" />
      <NavItem
        icon="⊟"
        label="All projects"
        count={counts.all}
        active={!filters.visibility && !filters.type && !filters.tag}
        onClick={() => onFilter({ visibility: null, type: null, tag: null })}
      />
      <NavItem
        icon={<span style={{ color: "var(--hub-accent-400)" }}>◎</span>}
        label="Public"
        count={counts.public}
        active={filters.visibility === "public"}
        onClick={() => onFilter({ visibility: filters.visibility === "public" ? null : "public" })}
      />
      <NavItem
        icon={<span style={{ color: "var(--hub-private-text)" }}>◉</span>}
        label="Private"
        count={counts.private}
        active={filters.visibility === "private"}
        onClick={() => onFilter({ visibility: filters.visibility === "private" ? null : "private" })}
      />

      <div className="hub-divider" />

      <NavSection label="By tag" />
      {allTags.map((tag) => (
        <NavItem
          key={tag}
          icon={<TagDot tag={tag} />}
          label={tag}
          count={counts.byTag[tag]}
          active={filters.tag === tag}
          onClick={() => onFilter({ tag: filters.tag === tag ? null : tag })}
        />
      ))}

      <div className="hub-divider" />

      <NavSection label="Type" />
      <NavItem
        icon="□"
        label="Internal"
        count={counts.internal}
        active={filters.type === "internal"}
        onClick={() => onFilter({ type: filters.type === "internal" ? null : "internal" })}
      />
      <NavItem
        icon="↓"
        label="Imported"
        count={counts.imported}
        active={filters.type === "imported"}
        onClick={() => onFilter({ type: filters.type === "imported" ? null : "imported" })}
      />
      <NavItem
        icon="⌁"
        label="Linked"
        count={counts.linked}
        active={filters.type === "linked"}
        onClick={() => onFilter({ type: filters.type === "linked" ? null : "linked" })}
      />
    </nav>
  );
}
