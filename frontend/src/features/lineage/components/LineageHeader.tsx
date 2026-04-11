interface LineageHeaderProps {
  graphKind?: "lineage" | "execution";
  modelName: string | null;
  contextMode: "single" | "multi";
  activeContext: string;
  activeContexts: string[];
  workflowSource: "framework_cli" | "fallback" | null;
  visibleCount: number;
  totalCount: number;
  isFiltered: boolean;
}

export function LineageHeader({
  graphKind = "lineage",
  modelName,
  contextMode,
  activeContext,
  activeContexts,
  workflowSource,
  visibleCount,
  totalCount,
  isFiltered,
}: LineageHeaderProps) {
  return (
    <div className="lg-header">
      <div className="lg-header-top">
        <span className="lg-title">{graphKind === "lineage" ? "Lineage" : "Execution"}</span>
        {modelName ? (
          <>
            <span className="lg-model-sep">·</span>
            <span className="lg-model-name">{modelName}</span>
          </>
        ) : null}
      </div>

      <div className="lg-pills">
        {contextMode === "single" ? <span className="lg-pill lg-pill-ctx">⬡ {activeContext}</span> : null}
        {contextMode === "multi" && activeContexts.length > 0 ? (
          <span className="lg-pill lg-pill-ctx">⬡ {activeContexts.join(", ")}</span>
        ) : null}
        {contextMode === "multi" && activeContexts.length === 0 ? (
          <span className="lg-pill lg-pill-neutral">⬡ no context</span>
        ) : null}

        {workflowSource === "framework_cli" ? <span className="lg-pill lg-pill-src-ok">● workflow cache</span> : null}
        {workflowSource === "fallback" ? <span className="lg-pill lg-pill-src-bad">⚠ fallback data</span> : null}

        {isFiltered && totalCount > 0 ? (
          <span className={`lg-pill ${visibleCount === 0 ? "lg-pill-zero" : "lg-pill-filter"}`}>
            {visibleCount === 0
              ? `0 ${graphKind === "lineage" ? "folders" : "steps"} visible`
              : `${visibleCount} of ${totalCount} ${graphKind === "lineage" ? "folders" : "steps"}`}
          </span>
        ) : null}
        {!isFiltered && totalCount > 0 ? (
          <span className="lg-pill lg-pill-neutral">{totalCount} {graphKind === "lineage" ? "folders" : "steps"}</span>
        ) : null}
      </div>
    </div>
  );
}
