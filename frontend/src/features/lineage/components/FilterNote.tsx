interface FilterNoteProps {
  searchTerm: string;
  searchHidden: number;
  contextHidden: number;
  visibleCount: number;
  onClearSearch: () => void;
  onClearAll: () => void;
}

export function FilterNote({
  searchTerm,
  searchHidden,
  contextHidden,
  visibleCount,
  onClearSearch: _onClearSearch,
  onClearAll,
}: FilterNoteProps) {
  const hasSearch = searchTerm.length > 0;
  const hasContext = contextHidden > 0;

  if (!hasSearch && !hasContext) return null;

  const parts: string[] = [];
  if (hasSearch) parts.push(`search "${searchTerm}" hides ${searchHidden} folder${searchHidden !== 1 ? "s" : ""}`);
  if (hasContext) parts.push(`context hides ${contextHidden} folder${contextHidden !== 1 ? "s" : ""}`);

  return (
    <div className="lg-filter-note">
      <span>
        Showing <strong>{visibleCount}</strong> folders
        {parts.length > 0 ? ` · ${parts.join(" · ")}` : ""}
      </span>
      <button className="lg-filter-note-clear" onClick={onClearAll} type="button">
        Clear all
      </button>
    </div>
  );
}
