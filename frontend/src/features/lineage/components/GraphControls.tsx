interface GraphControlsProps {
  onFitView: () => void;
  onReset: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export function GraphControls({ onFitView, onReset, onZoomIn, onZoomOut }: GraphControlsProps) {
  return (
    <div className="lg-graph-controls">
      <button className="lg-gc-btn" onClick={onFitView} title="Fit graph" type="button">
        ⊡
      </button>
      <button className="lg-gc-btn" onClick={onReset} title="Reset view" type="button">
        ↺
      </button>
      <button className="lg-gc-btn" onClick={onZoomIn} title="Zoom in" type="button">
        +
      </button>
      <button className="lg-gc-btn" onClick={onZoomOut} title="Zoom out" type="button">
        −
      </button>
    </div>
  );
}
