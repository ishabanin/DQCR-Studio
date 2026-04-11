import { useEffect, useMemo, useState } from "react";

import { WorkflowExecutionStep, WorkflowStepDetailResponse } from "../../../api/projects";

interface ExecutionDetailPanelProps {
  selectedStep: WorkflowExecutionStep | null;
  selectedStepDetail: WorkflowStepDetailResponse | undefined;
  isDetailLoading: boolean;
  inboundCount: number;
  outboundCount: number;
  onOpenStepSql: () => void;
  onNavigateWorkflowRef: (refName: string, refData: unknown) => void;
  onNavigateModelRef: (refName: string, refData: unknown) => void;
}

export function ExecutionDetailPanel({
  selectedStep,
  selectedStepDetail,
  isDetailLoading,
  inboundCount,
  outboundCount,
  onOpenStepSql,
  onNavigateWorkflowRef,
  onNavigateModelRef,
}: ExecutionDetailPanelProps) {
  if (!selectedStep) {
    return (
      <div className="lg-detail">
        <div className="lg-dp-empty">
          <div className="lg-dp-empty-icon">◫</div>
          <div className="lg-dp-empty-title">Select a step</div>
          <div className="lg-dp-empty-text">Click any step node to inspect scope, context and execution details.</div>
        </div>
      </div>
    );
  }

  const tools = Array.isArray(selectedStep.tools) ? selectedStep.tools : [];
  const sqlModel = (selectedStepDetail?.sql_model ?? null) as Record<string, unknown> | null;
  const sqlMetadata = (sqlModel?.metadata ?? null) as Record<string, unknown> | null;

  const preparedSql = useMemo(
    () => ((sqlModel?.prepared_sql ?? {}) as Record<string, unknown>),
    [sqlModel?.prepared_sql],
  );
  const renderedSql = useMemo(
    () => ((sqlModel?.rendered_sql ?? {}) as Record<string, unknown>),
    [sqlModel?.rendered_sql],
  );
  const sqlTools = useMemo(() => {
    const all = new Set<string>();
    Object.keys(preparedSql).forEach((tool) => all.add(tool));
    Object.keys(renderedSql).forEach((tool) => all.add(tool));
    if (tools.length > 0) {
      tools.forEach((tool) => all.add(tool));
    }
    return Array.from(all).sort((a, b) => a.localeCompare(b));
  }, [preparedSql, renderedSql, tools]);
  const [selectedTool, setSelectedTool] = useState<string>("source");

  useEffect(() => {
    if (sqlTools.length === 0) {
      setSelectedTool("source");
      return;
    }
    if (selectedTool !== "source" && !sqlTools.includes(selectedTool)) {
      setSelectedTool(sqlTools[0]);
    }
  }, [sqlTools, selectedTool]);

  const resolvedTool = selectedTool === "source" ? null : selectedTool;
  const selectedPreparedSql = resolvedTool ? preparedSql[resolvedTool] : null;
  const selectedRenderedSql = resolvedTool ? renderedSql[resolvedTool] : null;

  const workflowRefs = (sqlMetadata?.workflow_refs ?? {}) as Record<string, unknown>;
  const modelRefs = (sqlMetadata?.model_refs ?? {}) as Record<string, unknown>;
  const inlineQueryConfig = (sqlMetadata?.inline_query_config ?? null) as Record<string, unknown> | null;
  const inlineCteConfigs = (sqlMetadata?.inline_cte_configs ?? {}) as Record<string, unknown>;
  const inlineAttrConfigs = (sqlMetadata?.inline_attr_configs ?? {}) as Record<string, unknown>;
  const cteTableNames = ((sqlModel?.cte_table_names ?? {}) as Record<string, unknown>) ?? {};
  const targetTable = sqlModel?.target_table;
  const materialization = sqlModel?.materialization;
  const cteMaterialization = sqlModel?.cte_materialization;
  const attributes = Array.isArray(sqlModel?.attributes) ? sqlModel?.attributes : [];

  return (
    <div className="lg-detail">
      <div className="lg-dp-head">
        <div className="lg-dp-name">{selectedStep.name || selectedStep.step_id}</div>
        <div className="lg-dp-path">{selectedStep.step_id}</div>
      </div>

      <div className="lg-dp-body">
        <div className="lg-dp-section lg-dp-section-top">
          <div className="lg-dp-section-label">Scope</div>
          <div className="lg-mat-badge">{selectedStep.step_scope}</div>
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

        <div className="lg-dp-sep" />
        <div className="lg-dp-section">
          <div className="lg-dp-section-label">Context</div>
          <div>{selectedStep.context}</div>
        </div>

        <div className="lg-dp-sep" />
        <div className="lg-dp-section">
          <div className="lg-dp-section-label">Type</div>
          <div>{selectedStep.step_type}</div>
        </div>

        {tools.length > 0 ? (
          <>
            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">Tools</div>
              <div className="lg-chips-wrap">
                {tools.map((tool) => (
                  <span key={tool} className="lg-chip">
                    {tool}
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : null}

        {selectedStep.has_sql_model ? (
          <>
            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">SQL Step</div>
              <button className="lg-state-btn" onClick={onOpenStepSql} type="button" disabled={isDetailLoading}>
                {isDetailLoading ? "Loading…" : "Open SQL"}
              </button>
              {typeof sqlModel?.path === "string" && sqlModel.path ? <div className="lg-dp-path">{sqlModel.path}</div> : null}
            </div>

            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">Materialization</div>
              <div className="lg-chips-wrap">
                {materialization ? <span className="lg-chip">{String(materialization)}</span> : <span className="lg-chip">n/a</span>}
                {cteMaterialization ? <span className="lg-chip">cte: {String(cteMaterialization)}</span> : null}
              </div>
            </div>

            {targetTable ? (
              <>
                <div className="lg-dp-sep" />
                <div className="lg-dp-section">
                  <div className="lg-dp-section-label">Target Table</div>
                  <div className="lg-dp-path">{String(targetTable)}</div>
                </div>
              </>
            ) : null}

            {attributes.length > 0 ? (
              <>
                <div className="lg-dp-sep" />
                <div className="lg-dp-section">
                  <div className="lg-dp-section-label">Attributes</div>
                  <div className="lg-chips-wrap">
                    {attributes.map((item, index) => {
                      const row = item as Record<string, unknown>;
                      const name = typeof row.name === "string" ? row.name : `attr_${index + 1}`;
                      return (
                        <span key={`${name}-${index}`} className="lg-chip">
                          {name}
                        </span>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : null}

            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">SQL by Tool</div>
              <div className="lg-chips-wrap">
                <button
                  className={`lg-ref-btn ${selectedTool === "source" ? "active" : ""}`}
                  onClick={() => setSelectedTool("source")}
                  type="button"
                >
                  source
                </button>
                {sqlTools.map((tool) => (
                  <button
                    key={tool}
                    className={`lg-ref-btn ${selectedTool === tool ? "active" : ""}`}
                    onClick={() => setSelectedTool(tool)}
                    type="button"
                  >
                    {tool}
                  </button>
                ))}
              </div>
              <div className="lg-sql-block-wrap">
                <div className="lg-sql-block-title">Source SQL</div>
                <pre className="lg-sql-block">{String(sqlModel?.source_sql ?? "")}</pre>
              </div>
              {resolvedTool ? (
                <>
                  <div className="lg-sql-block-wrap">
                    <div className="lg-sql-block-title">Prepared SQL ({resolvedTool})</div>
                    <pre className="lg-sql-block">{String(selectedPreparedSql ?? "")}</pre>
                  </div>
                  <div className="lg-sql-block-wrap">
                    <div className="lg-sql-block-title">Rendered SQL ({resolvedTool})</div>
                    <pre className="lg-sql-block">{String(selectedRenderedSql ?? "")}</pre>
                  </div>
                </>
              ) : null}
            </div>

            {Object.keys(workflowRefs).length > 0 || Object.keys(modelRefs).length > 0 ? (
              <>
                <div className="lg-dp-sep" />
                <div className="lg-dp-section">
                  <div className="lg-dp-section-label">Refs</div>
                  <div className="lg-chips-wrap">
                    {Object.entries(workflowRefs).map(([refName, refData]) => (
                      <button
                        key={refName}
                        className="lg-ref-btn"
                        onClick={() => onNavigateWorkflowRef(refName, refData)}
                        type="button"
                        title="Navigate to workflow step"
                      >
                        {refName}
                      </button>
                    ))}
                    {Object.entries(modelRefs).map(([refName, refData]) => (
                      <button
                        key={refName}
                        className="lg-ref-btn"
                        onClick={() => onNavigateModelRef(refName, refData)}
                        type="button"
                        title="Navigate to model object"
                      >
                        {refName}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            ) : null}

            {Object.keys(cteTableNames).length > 0 || inlineQueryConfig || Object.keys(inlineCteConfigs).length > 0 || Object.keys(inlineAttrConfigs).length > 0 ? (
              <>
                <div className="lg-dp-sep" />
                <div className="lg-dp-section">
                  <div className="lg-dp-section-label">CTE / Inline Config</div>
                  {Object.keys(cteTableNames).length > 0 ? (
                    <div className="lg-sql-block-wrap">
                      <div className="lg-sql-block-title">cte_table_names</div>
                      <pre className="lg-sql-block">{JSON.stringify(cteTableNames, null, 2)}</pre>
                    </div>
                  ) : null}
                  {inlineQueryConfig ? (
                    <div className="lg-sql-block-wrap">
                      <div className="lg-sql-block-title">inline_query_config</div>
                      <pre className="lg-sql-block">{JSON.stringify(inlineQueryConfig, null, 2)}</pre>
                    </div>
                  ) : null}
                  {Object.keys(inlineCteConfigs).length > 0 ? (
                    <div className="lg-sql-block-wrap">
                      <div className="lg-sql-block-title">inline_cte_configs</div>
                      <pre className="lg-sql-block">{JSON.stringify(inlineCteConfigs, null, 2)}</pre>
                    </div>
                  ) : null}
                  {Object.keys(inlineAttrConfigs).length > 0 ? (
                    <div className="lg-sql-block-wrap">
                      <div className="lg-sql-block-title">inline_attr_configs</div>
                      <pre className="lg-sql-block">{JSON.stringify(inlineAttrConfigs, null, 2)}</pre>
                    </div>
                  ) : null}
                </div>
              </>
            ) : null}
          </>
        ) : null}

        {selectedStep.has_param_model ? (
          <>
            <div className="lg-dp-sep" />
            <div className="lg-dp-section">
              <div className="lg-dp-section-label">Parameter Step</div>
              <div>{selectedStep.name || "param"}</div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
