import type { SqlViewMode } from "../types/sqlView";

interface SqlModeBarProps {
  mode: SqlViewMode;
  onModeChange: (mode: SqlViewMode) => void;
  tools: string[];
  selectedTool: string | null;
  onToolChange: (tool: string) => void;
  hasWorkflowCache: boolean;
  onToggleFullscreen?: () => void;
}

export default function SqlModeBar({
  mode,
  onModeChange,
  tools,
  selectedTool,
  onToolChange,
  hasWorkflowCache,
  onToggleFullscreen,
}: SqlModeBarProps) {
  return (
    <div className="sql-mode-bar">
      <div className="sql-mode-tabs" role="tablist" aria-label="SQL view mode">
        {(["source", "prepared", "rendered"] as const).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={mode === item}
            className={mode === item ? "sql-mode-tab sql-mode-tab-active" : "sql-mode-tab"}
            onClick={() => onModeChange(item)}
          >
            {item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      {mode !== "source" ? (
        <div className="sql-tool-switcher">
          {hasWorkflowCache ? (
            tools.length > 0 ? (
              <div className="sql-tool-chip-list" role="radiogroup" aria-label="SQL tool">
                {tools.map((tool) => (
                  <button
                    key={tool}
                    type="button"
                    role="radio"
                    aria-checked={selectedTool === tool}
                    className={selectedTool === tool ? "sql-tool-chip sql-tool-chip-active" : "sql-tool-chip"}
                    onClick={() => onToolChange(tool)}
                  >
                    {tool}
                  </button>
                ))}
              </div>
            ) : (
              <span className="sql-mode-placeholder">Нет доступных tools в workflow cache</span>
            )
          ) : (
            <span className="sql-mode-placeholder">Кэш недоступен, переключитесь в Source</span>
          )}
        </div>
      ) : null}
      <button type="button" className="sql-fullscreen-toggle-btn" onClick={onToggleFullscreen} title="Fullscreen (Ctrl+Shift+Enter)">
        ⛶
      </button>
    </div>
  );
}
