import { useState, useEffect, useRef, useMemo } from 'react';
import { getSqlFile } from '../../api';
import { AttributeTable } from './AttributeTable';
import { highlightSql } from '../../utils/highlightSql';

type SqlViewMode = 'source' | 'prepared' | 'rendered';

interface TableInfo {
  alias: string;
  is_variable: boolean;
  is_cte: boolean;
  model_ref?: string;
}

interface SqlViewerProps {
  sql?: {
    name?: string;
    path?: string;
    source_sql?: string;
    prepared_sql?: Record<string, string>;
    rendered_sql?: Record<string, string>;
    metadata?: {
      parameters?: string[];
      tables?: Record<string, TableInfo>;
      aliases?: Array<{ alias: string; source: string; expression: string }>;
      ctes?: Record<string, any>;
      model_refs?: Record<string, string>;
    };
    attributes?: Array<{
      name: string;
      domain_type?: string;
      required?: boolean;
      default_value?: string;
      constraints?: string[];
      distribution_key?: number | null;
      partition_key?: number | null;
    }>;
    materialization?: string;
    context?: string;
    contexts?: string[];
    target_table?: string;
  };
  sourceFilePath?: string;
  name?: string;
  folder?: string;
  dependencies?: string[];
  context?: string;
  projectContexts?: string[];
  onParamClick?: (paramName: string) => void;
  onTableClick?: (tableName: string) => void;
}

export function SqlViewer({ sql, sourceFilePath, name, folder, dependencies, onParamClick, onTableClick, projectContexts }: SqlViewerProps) {
  const [viewMode, setViewMode] = useState<SqlViewMode>('source');
  const [selectedTool, setSelectedTool] = useState<string>('');
  const [sourceSql, setSourceSql] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    params: true,
    tables: true,
    attrs: true,
    deps: true,
    target: true,
    sql: true,
  });
  const codeRef = useRef<HTMLElement>(null);

  const tools = sql?.prepared_sql ? Object.keys(sql.prepared_sql) : [];
  const allContexts = sql?.contexts || projectContexts || (sql?.context ? [sql.context] : []);
  const uniqueContexts = [...new Set(allContexts)];

  useEffect(() => {
    if (sourceFilePath) {
      setLoading(true);
      getSqlFile(sourceFilePath)
        .then(data => setSourceSql(data.content))
        .catch(err => {
          console.error('Failed to load SQL file:', err);
          setSourceSql(null);
        })
        .finally(() => setLoading(false));
    } else if (sql?.source_sql) {
      setSourceSql(sql.source_sql);
    } else {
      setSourceSql(null);
    }
  }, [sourceFilePath, sql?.source_sql]);

  const getSqlContent = (): string => {
    if (viewMode === 'source') {
      return sourceSql || sql?.source_sql || '';
    }
    if (viewMode === 'prepared' && tools.length > 0) {
      return sql?.prepared_sql?.[selectedTool || tools[0]] || '';
    }
    if (viewMode === 'rendered' && tools.length > 0) {
      return sql?.rendered_sql?.[selectedTool || tools[0]] || '';
    }
    return '';
  };

  const sqlContent = useMemo(() => getSqlContent(), [viewMode, selectedTool, sourceSql, sql, tools]);
  
  const sqlCodeHtml = useMemo(() => {
    return highlightSql(sqlContent, sql?.metadata?.tables);
  }, [sqlContent, sql?.metadata?.tables]);

  const handleParamClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains('sql-param') && onParamClick) {
      const paramName = target.getAttribute('data-param');
      if (paramName) {
        onParamClick(paramName);
      }
    }
    if (target.classList.contains('sql-table') && onTableClick) {
      const tableName = target.getAttribute('data-table');
      if (tableName) {
        onTableClick(tableName);
      }
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleToolSelect = (tool: string) => {
    setSelectedTool(tool);
  };

  const mergedAttributes = useMemo(() => {
    if (!sql?.metadata?.aliases || sql.metadata.aliases.length === 0) {
      return sql?.attributes || [];
    }
    const attrsMap = new Map<string, any>();
    sql.attributes?.forEach(attr => {
      attrsMap.set(attr.name, attr);
    });
    return sql.metadata.aliases.map(alias => {
      const configAttr = attrsMap.get(alias.alias) || {};
      return {
        name: alias.alias,
        expression: alias.expression,
        domain_type: configAttr.domain_type,
        constraints: configAttr.constraints,
        required: configAttr.required,
        distribution_key: configAttr.distribution_key,
        partition_key: configAttr.partition_key,
      };
    });
  }, [sql?.metadata?.aliases, sql?.attributes]);

  return (
    <div className="sql-viewer">
      <div className="viewer-header">
        <h2>📄 {name || sql?.name || 'SQL Query'}</h2>
        <div className="header-badges">
          {folder && <span className="badge badge-info">{folder}</span>}
          {uniqueContexts.length > 0 && (
            <div className="context-badges">
              {uniqueContexts.map(ctx => (
                <span key={ctx} className="badge badge-success">{ctx}</span>
              ))}
            </div>
          )}
          {sql?.materialization && <span className="badge badge-primary">{sql.materialization}</span>}
        </div>
      </div>

      {sql?.metadata?.parameters && sql.metadata.parameters.length > 0 && (
        <div className={`detail-section accordion-item ${expandedSections.params ? 'expanded' : ''}`}>
          <div className="accordion-header" onClick={() => toggleSection('params')}>
            <span className="accordion-icon">{expandedSections.params ? '▼' : '▶'}</span>
            <h4>Parameters ({sql.metadata.parameters.length})</h4>
          </div>
          {expandedSections.params && (
            <div className="accordion-content">
              <div className="param-tags">
                {sql.metadata.parameters.map((param, i) => (
                  <span key={i} className="param-tag" onClick={() => onParamClick?.(param)}>
                    {param}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {sql?.metadata?.tables && Object.keys(sql.metadata.tables).length > 0 && (
        <div className={`detail-section accordion-item ${expandedSections.tables ? 'expanded' : ''}`}>
          <div className="accordion-header" onClick={() => toggleSection('tables')}>
            <span className="accordion-icon">{expandedSections.tables ? '▼' : '▶'}</span>
            <h4>Tables ({Object.keys(sql.metadata.tables).length})</h4>
          </div>
          {expandedSections.tables && (
            <div className="accordion-content">
              <div className="table-list">
                {Object.entries(sql.metadata.tables).map(([table, info]: [string, any]) => (
                  <div key={table} className="table-item">
                    <span className={`table-badge ${info.is_variable ? 'variable' : ''} ${info.is_cte ? 'cte' : ''}`}>
                      {info.is_variable ? '📋' : info.is_cte ? '🔷' : '📗'}
                    </span>
                    <span className="table-alias">{info.alias}</span>
                    <span className="table-name" onClick={() => onTableClick?.(table)}>{table}</span>
                    {info.model_ref && <span className="table-model-ref">→ {info.model_ref}</span>}
                  </div>
                ))}
              </div>
              {sql?.metadata?.model_refs && Object.keys(sql.metadata.model_refs).length > 0 && (
                <div className="model-refs-section">
                  <h5>Model References</h5>
                  {Object.entries(sql.metadata.model_refs).map(([ref, info]: [string, any]) => (
                    <div key={ref} className="model-ref-item">
                      <span className="model-ref-key">{ref}</span>
                      <span className="model-ref-path">→ {info.path}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {mergedAttributes.length > 0 && (
        <div className={`detail-section accordion-item ${expandedSections.attrs ? 'expanded' : ''}`}>
          <div className="accordion-header" onClick={() => toggleSection('attrs')}>
            <span className="accordion-icon">{expandedSections.attrs ? '▼' : '▶'}</span>
            <h4>ATTRIBUTES ({mergedAttributes.length})</h4>
          </div>
          {expandedSections.attrs && (
            <div className="accordion-content">
              <AttributeTable 
                attributes={mergedAttributes} 
                tables={sql?.metadata?.tables}
                onParamClick={onParamClick}
                onTableClick={onTableClick}
              />
            </div>
          )}
        </div>
      )}

      {dependencies && dependencies.length > 0 && (
        <div className={`detail-section accordion-item ${expandedSections.deps ? 'expanded' : ''}`}>
          <div className="accordion-header" onClick={() => toggleSection('deps')}>
            <span className="accordion-icon">{expandedSections.deps ? '▼' : '▶'}</span>
            <h4>Dependencies ({dependencies.length})</h4>
          </div>
          {expandedSections.deps && (
            <div className="accordion-content">
              <div className="dep-list">
                {dependencies.map((dep, i) => (
                  <span key={i} className="dep-tag">{dep}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {sql?.target_table && (
        <div className={`detail-section accordion-item ${expandedSections.target ? 'expanded' : ''}`}>
          <div className="accordion-header" onClick={() => toggleSection('target')}>
            <span className="accordion-icon">{expandedSections.target ? '▼' : '▶'}</span>
            <h4>Target Table</h4>
          </div>
          {expandedSections.target && (
            <div className="accordion-content">
              <span className="target-table">{sql.target_table}</span>
            </div>
          )}
        </div>
      )}

      <div className={`detail-section accordion-item ${expandedSections.sql ? 'expanded' : ''}`}>
        <div className="accordion-header" onClick={() => toggleSection('sql')}>
          <span className="accordion-icon">{expandedSections.sql ? '▼' : '▶'}</span>
          <h3>SQL</h3>
        </div>
        {expandedSections.sql && (
          <div className="accordion-content sql-code-content">
            <div className="sql-tabs-container">
              <div className="sql-mode-tabs">
                <button 
                  className={`sql-mode-tab ${viewMode === 'source' ? 'active' : ''}`}
                  onClick={() => setViewMode('source')}
                >
                  Source
                </button>
                <button 
                  className={`sql-mode-tab ${viewMode === 'prepared' ? 'active' : ''}`}
                  onClick={() => setViewMode('prepared')}
                  disabled={tools.length === 0}
                >
                  Prepared
                </button>
                <button 
                  className={`sql-mode-tab ${viewMode === 'rendered' ? 'active' : ''}`}
                  onClick={() => setViewMode('rendered')}
                  disabled={tools.length === 0}
                >
                  Rendered
                </button>
                {viewMode !== 'source' && tools.length > 0 && (
                  <>
                    <span className="sql-tabs-divider"></span>
                    {tools.map(tool => (
                      <button
                        key={tool}
                        className={`sql-mode-tab tool-tab ${selectedTool === tool || (!selectedTool && tool === tools[0]) ? 'active' : ''}`}
                        onClick={() => handleToolSelect(tool)}
                      >
                        {tool}
                      </button>
                    ))}
                  </>
                )}
              </div>
            </div>
            <div className="sql-code-wrapper">
              {loading ? (
                <pre className="sql-code">Loading...</pre>
              ) : sqlContent ? (
                <pre 
                  className="sql-code"
                  onClick={handleParamClick}
                >
                  <code 
                    ref={codeRef}
                    dangerouslySetInnerHTML={{ __html: sqlCodeHtml }}
                  />
                </pre>
              ) : (
                <pre className="sql-code">-- No SQL content</pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
