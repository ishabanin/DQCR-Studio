import { useEffect, useRef, useState } from "react";

import type { SqlViewMode } from "../types/sqlView";

interface SqlFullscreenOverlayProps {
  fileName: string;
  isDirty: boolean;
  mode: SqlViewMode;
  onModeChange: (mode: SqlViewMode) => void;
  tools: string[];
  selectedTool: string | null;
  onToolChange: (tool: string) => void;
  onSave: () => void;
  onFormat: () => void;
  onExit: () => void;
}

export default function SqlFullscreenOverlay({
  fileName,
  isDirty,
  mode,
  onModeChange,
  tools,
  selectedTool,
  onToolChange,
  onSave,
  onFormat,
  onExit,
}: SqlFullscreenOverlayProps) {
  const [visible, setVisible] = useState(true);
  const timerRef = useRef<number | null>(null);

  const scheduleHide = () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(() => {
      setVisible(false);
      timerRef.current = null;
    }, 2000);
  };

  useEffect(() => {
    setVisible(true);
    scheduleHide();

    const showAndReschedule = () => {
      setVisible(true);
      scheduleHide();
    };
    window.addEventListener("mousemove", showAndReschedule);
    window.addEventListener("keydown", showAndReschedule);
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
      window.removeEventListener("mousemove", showAndReschedule);
      window.removeEventListener("keydown", showAndReschedule);
    };
  }, []);

  return (
    <div className={visible ? "sql-fullscreen-overlay" : "sql-fullscreen-overlay sql-fullscreen-overlay-hidden"}>
      <div className="sql-fullscreen-file">
        {fileName}
        {isDirty ? <span className="sql-fullscreen-dirty">●</span> : null}
      </div>
      <div className="sql-fullscreen-controls">
        <div className="sql-fullscreen-mode-group">
          {(["source", "prepared", "rendered"] as const).map((item) => (
            <button
              key={item}
              type="button"
              className={mode === item ? "sql-fullscreen-chip sql-fullscreen-chip-active" : "sql-fullscreen-chip"}
              onClick={() => onModeChange(item)}
            >
              {item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </div>
        {mode !== "source" ? (
          <div className="sql-fullscreen-tool-group">
            {tools.map((tool) => (
              <button
                key={tool}
                type="button"
                className={selectedTool === tool ? "sql-fullscreen-chip sql-fullscreen-chip-active" : "sql-fullscreen-chip"}
                onClick={() => onToolChange(tool)}
              >
                {tool}
              </button>
            ))}
          </div>
        ) : null}
        <button type="button" className="action-btn action-btn-primary" onClick={onSave} disabled={mode !== "source"}>
          Save
        </button>
        {mode === "source" ? (
          <button type="button" className="action-btn" onClick={onFormat}>
            Format
          </button>
        ) : null}
        <button type="button" className="action-btn" onClick={onExit}>
          ✕ Выйти
        </button>
      </div>
    </div>
  );
}
