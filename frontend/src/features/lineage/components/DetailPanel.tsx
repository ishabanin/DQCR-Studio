import { LineageNode } from "../../../api/projects";

interface DetailPanelProps {
  selectedNode: LineageNode | null;
  onOpenQuery: (filePath: string) => void;
  inboundCount: number;
  outboundCount: number;
  modelId: string;
  formatPath: (path: string, modelId: string) => string;
}

export function DetailPanel({
  selectedNode,
  onOpenQuery,
  inboundCount,
  outboundCount,
  modelId,
  formatPath,
}: DetailPanelProps) {
  if (!selectedNode) {
    return (
      <div className="lg-detail">
        <div className="lg-dp-empty">
          <div className="lg-dp-empty-icon">◫</div>
          <div className="lg-dp-empty-title">Select a folder</div>
          <div className="lg-dp-empty-text">Click any folder node to inspect its queries, parameters and CTEs</div>
        </div>
      </div>
    );
  }

  return (
    <div className="lg-detail">
      <div className="lg-dp-head">
        <div className="lg-dp-name">{selectedNode.name}</div>
        <div className="lg-dp-path">{formatPath(selectedNode.path, modelId)}</div>
      </div>

      <div className="lg-dp-body">
        <div className="lg-dp-section lg-dp-section-top">
          <div className="lg-dp-section-label">Materialization</div>
          <div className="lg-mat-badge">{selectedNode.materialized}</div>
        </div>

        <div className="lg-dp-sep" />

        <div className="lg-dp-conn-row">
          <div className="lg-dp-conn-item">
            <div className="lg-dp-conn-label">Inbound</div>
            <div className="lg-dp-conn-val">{inboundCount}</div>
            <div className="lg-dp-conn-sub">{inboundCount === 1 ? "dependency" : "dependencies"}</div>
          </div>
          <div className="lg-dp-conn-item">
            <div className="lg-dp-conn-label">Outbound</div>
            <div className="lg-dp-conn-val">{outboundCount}</div>
            <div className="lg-dp-conn-sub">{outboundCount === 1 ? "dependent step" : "dependent steps"}</div>
          </div>
        </div>

        {selectedNode.parameters.length > 0 ? (
          <>
            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">Parameters</div>
              <div className="lg-chips-wrap">
                {selectedNode.parameters.map((parameter) => (
                  <span key={parameter} className="lg-chip">
                    {parameter}
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : null}

        {selectedNode.ctes.length > 0 ? (
          <>
            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">CTEs</div>
              <div className="lg-chips-wrap">
                {selectedNode.ctes.map((cte) => (
                  <span key={cte} className="lg-chip">
                    {cte}
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : null}

        {selectedNode.queries.length > 0 ? (
          <>
            <div className="lg-dp-sep" />
            <div className="lg-dp-section lg-dp-section-queries">
              <div className="lg-dp-section-label">SQL queries</div>
            </div>
            {selectedNode.queries.map((queryName) => (
              <div
                key={queryName}
                className="lg-query-row"
                onClick={() => onOpenQuery(`${selectedNode.path}/${queryName}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onOpenQuery(`${selectedNode.path}/${queryName}`);
                  }
                }}
              >
                <span className="lg-query-icon">f</span>
                <span className="lg-query-name">{queryName}</span>
                <span className="lg-query-open">Open →</span>
              </div>
            ))}
          </>
        ) : null}
      </div>
    </div>
  );
}
