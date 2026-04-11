interface FallbackBannerProps {
  graphKind?: "lineage" | "execution";
  source: "framework_cli" | "fallback" | null;
  status: "ready" | "stale" | "building" | "error" | "missing" | null;
  isRebuilding: boolean;
  onRebuild: () => void;
}

export function FallbackBanner({ graphKind = "lineage", source, status, isRebuilding, onRebuild }: FallbackBannerProps) {
  const isFallbackProblem = source === "fallback" && (status === "stale" || status === "error");
  if (!isFallbackProblem) return null;

  return (
    <div className="lg-banner">
      <span className="lg-banner-icon">⚠</span>
      <div className="lg-banner-text">
        <span className="lg-banner-strong">
          {status === "error" ? "Workflow cache build failed" : "Workflow cache is stale"}
        </span>
        <span className="lg-banner-sub">
          — {graphKind === "lineage" ? "graph built from file structure" : "execution payload fallback"}.
          Some data may be incomplete.
        </span>
      </div>
      <button className="lg-banner-btn" onClick={onRebuild} disabled={isRebuilding} type="button">
        {isRebuilding ? "Rebuilding…" : "↻ Rebuild cache"}
      </button>
    </div>
  );
}
