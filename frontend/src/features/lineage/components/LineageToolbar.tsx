type LineageViewMode = "horizontal" | "vertical" | "compact";
type GraphKind = "lineage" | "execution";

interface LineageToolbarProps {
  models: string[];
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  graphKind: GraphKind;
  onGraphKindChange: (kind: GraphKind) => void;
  toolOptions?: string[];
  selectedTool?: string;
  onToolChange?: (tool: string) => void;
  viewMode: LineageViewMode;
  onViewMode: (mode: LineageViewMode) => void;
  search: string;
  onSearch: (value: string) => void;
  onExport: () => void;
}

export function LineageToolbar({
  models,
  selectedModel,
  onModelChange,
  graphKind,
  onGraphKindChange,
  toolOptions = [],
  selectedTool = "all_tools",
  onToolChange,
  viewMode,
  onViewMode,
  search,
  onSearch,
  onExport,
}: LineageToolbarProps) {
  return (
    <div className="lg-toolbar">
      <div className="lg-tb-group">
        <select
          className="lg-select"
          style={{ minWidth: 160, maxWidth: 200 }}
          value={selectedModel}
          onChange={(event) => onModelChange(event.target.value)}
        >
          {models.map((modelId) => (
            <option key={modelId} value={modelId}>
              {modelId}
            </option>
          ))}
        </select>
      </div>

      <div className="lg-tb-sep" />

      <div className="lg-tb-group">
        <div className="lg-mode-tog">
          {(["lineage", "execution"] as const).map((mode) => (
            <button
              key={mode}
              className={`lg-mode-btn ${graphKind === mode ? "active" : ""}`}
              onClick={() => onGraphKindChange(mode)}
              title={mode === "lineage" ? "Folder-level lineage graph" : "Step-level execution graph"}
              type="button"
            >
              {mode === "lineage" ? "Lineage" : "Execution"}
            </button>
          ))}
        </div>
      </div>

      <div className="lg-tb-sep" />

      {graphKind === "execution" ? (
        <>
          <div className="lg-tb-group">
            <select
              className="lg-select"
              style={{ minWidth: 130, maxWidth: 200 }}
              value={selectedTool}
              onChange={(event) => onToolChange?.(event.target.value)}
            >
              <option value="all_tools">All tools</option>
              {toolOptions.map((tool) => (
                <option key={tool} value={tool}>
                  {tool}
                </option>
              ))}
            </select>
          </div>
          <div className="lg-tb-sep" />
        </>
      ) : null}

      <div className="lg-tb-group">
        <div className="lg-mode-tog">
          {(["horizontal", "vertical", "compact"] as const).map((mode) => (
            <button
              key={mode}
              className={`lg-mode-btn ${viewMode === mode ? "active" : ""}`}
              onClick={() => onViewMode(mode)}
              title={mode === "compact" ? "Show folder names only" : `${mode} layout`}
              type="button"
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="lg-tb-sep" />

      <div className="lg-tb-group" style={{ flex: 1, maxWidth: 280 }}>
        <div className={`lg-search-wrap ${search ? "has-value" : ""}`}>
          <span className="lg-search-icon">⌕</span>
          <input
            className="lg-search-input"
            placeholder={graphKind === "lineage" ? "Search folders, queries…" : "Search steps, scopes, ids…"}
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
          <button className="lg-search-clear" onClick={() => onSearch("")} aria-label="Clear search" type="button">
            ✕
          </button>
        </div>
      </div>

      <div className="lg-tb-spacer" />

      <button className="lg-tb-btn" onClick={onExport} title="Export visible graph as PNG" type="button">
        <span>↗</span>
        <span>Export PNG</span>
      </button>
    </div>
  );
}
