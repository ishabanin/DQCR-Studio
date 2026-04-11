interface FilterNoteProps {
  graphKind?: "lineage" | "execution";
  searchTerm: string;
  searchHidden: number;
  overlayHidden: number;
  overlayLabel?: string;
  visibleCount: number;
  onClearSearch: () => void;
  onClearAll: () => void;
}

export function FilterNote({
  graphKind = "lineage",
  searchTerm,
  searchHidden,
  overlayHidden,
  overlayLabel = "context",
  visibleCount,
  onClearSearch,
  onClearAll,
}: FilterNoteProps) {
  const unit = graphKind === "lineage" ? "folder" : "step";
  const hasSearch = searchTerm.length > 0;
  const hasOverlay = overlayHidden > 0;

  if (!hasSearch && !hasOverlay) return null;

  const parts: string[] = [];
  if (hasSearch) parts.push(`search "${searchTerm}" hides ${searchHidden} ${unit}${searchHidden !== 1 ? "s" : ""}`);
  if (hasOverlay) parts.push(`${overlayLabel} hides ${overlayHidden} ${unit}${overlayHidden !== 1 ? "s" : ""}`);

  return (
    <div className="lg-filter-note">
      <span>
        Showing <strong>{visibleCount}</strong> {unit}s
        {parts.length > 0 ? ` · ${parts.join(" · ")}` : ""}
      </span>
      {hasSearch ? (
        <button className="lg-filter-note-clear" onClick={onClearSearch} type="button">
          Clear search
        </button>
      ) : null}
      <button className="lg-filter-note-clear" onClick={onClearAll} type="button">
        Clear all
      </button>
    </div>
  );
}
