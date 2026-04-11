interface LineageSummaryProps {
  graphKind?: "lineage" | "execution";
  folders: number;
  queries: number;
  params: number;
  ctes: number;
  isFiltered: boolean;
  source: "framework_cli" | "fallback" | null;
  visibleFolders?: number;
}

export function LineageSummary({
  graphKind = "lineage",
  folders,
  queries,
  params,
  ctes,
  isFiltered,
  source,
  visibleFolders,
}: LineageSummaryProps) {
  const note = isFiltered
    ? `Filtered · ${source === "fallback" ? "from file structure" : "model totals"}`
    : source === "fallback"
      ? "Model totals · from file structure"
      : "Model totals";

  return (
    <div className="lg-summary">
      <span className="lg-sum-badge">
        <b>{isFiltered && visibleFolders !== undefined ? visibleFolders : folders}</b>
        {isFiltered && visibleFolders !== undefined && visibleFolders !== folders ? ` / ${folders}` : ""}{" "}
        {graphKind === "lineage" ? "folders" : "steps"}
      </span>
      <span className="lg-sum-badge">
        <b>{queries}</b> {graphKind === "lineage" ? "queries" : "sql steps"}
      </span>
      <span className="lg-sum-badge">
        <b>{params}</b> params
      </span>
      {ctes > 0 ? (
        <span className="lg-sum-badge">
          <b>{ctes}</b> CTEs
        </span>
      ) : null}
      <span className="lg-sum-note">{note}</span>
    </div>
  );
}
