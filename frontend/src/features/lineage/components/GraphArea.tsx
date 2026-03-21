import { ReactNode } from "react";

import { GraphControls } from "./GraphControls";
import { GraphLegend } from "./GraphLegend";

interface GraphAreaProps {
  children: ReactNode;
  showLegend: boolean;
  onFitView: () => void;
  onReset: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export function GraphArea({ children, showLegend, onFitView, onReset, onZoomIn, onZoomOut }: GraphAreaProps) {
  return (
    <div className="lg-graph-area">
      {children}
      {showLegend ? <GraphLegend /> : null}
      <GraphControls onFitView={onFitView} onReset={onReset} onZoomIn={onZoomIn} onZoomOut={onZoomOut} />
    </div>
  );
}
