interface FallbackBannerProps {
  source: "framework_cli" | "fallback" | null;
  isRebuilding: boolean;
  onRebuild: () => void;
}

export function FallbackBanner({ source, isRebuilding, onRebuild }: FallbackBannerProps) {
  if (source !== "fallback") return null;

  return (
    <div className="lg-banner">
      <span className="lg-banner-icon">⚠</span>
      <div className="lg-banner-text">
        <span className="lg-banner-strong">Workflow cache is stale</span>
        <span className="lg-banner-sub">— graph built from file structure. Some data may be incomplete.</span>
      </div>
      <button className="lg-banner-btn" onClick={onRebuild} disabled={isRebuilding} type="button">
        {isRebuilding ? "Rebuilding…" : "↻ Rebuild cache"}
      </button>
    </div>
  );
}
