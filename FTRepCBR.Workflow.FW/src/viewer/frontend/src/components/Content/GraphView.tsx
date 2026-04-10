import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { WorkflowModel, WorkflowStep } from '../../types';

const getMermaidTheme = () => {
  const theme = document.documentElement.getAttribute('data-theme');
  return theme === 'light' ? 'light' : 'dark';
};

mermaid.initialize({
  startOnLoad: false,
  theme: getMermaidTheme(),
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis'
  }
});

interface GraphViewProps {
  workflow: WorkflowModel;
  context: string;
  onStepClick: (step: WorkflowStep) => void;
}

const SCOPE_COLORS: Record<string, string> = {
  flags: '#6c757d',
  pre: '#0d6efd',
  params: '#ffc107',
  sql: '#198754',
  post: '#dc3545'
};

export function GraphView({ workflow, context, onStepClick }: GraphViewProps) {
  const mermaidRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState(getMermaidTheme());

  useEffect(() => {
    const observer = new MutationObserver(() => {
      const newTheme = getMermaidTheme();
      setTheme(newTheme);
      mermaid.initialize({ theme: newTheme });
    });
    
    observer.observe(document.documentElement, { 
      attributes: true, 
      attributeFilter: ['data-theme'] 
    });

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!workflow || !workflow.steps.length) return;

    const generateMermaid = () => {
      const nodes: string[] = [];
      const edges: string[] = [];
      const nodeIds = new Set<string>();

      workflow.steps.forEach((step) => {
        const isActive = context === 'all' || step.context === context || step.context === 'all';
        const nodeId = step.full_name.replace(/[^a-zA-Z0-9_]/g, '_');
        
        const label = `${step.name}\\n(${step.step_type})`;
        
        nodes.push(`${nodeId}((${label}))`);
        nodeIds.add(nodeId);

        if (!isActive) {
          edges.push(`style ${nodeId} fill:#3c3c3c`);
        }
      });

      workflow.steps.forEach((step) => {
        const childId = step.full_name.replace(/[^a-zA-Z0-9_]/g, '_');
        step.dependencies.forEach((dep) => {
          const parentId = dep.replace(/[^a-zA-Z0-9_]/g, '_');
          if (nodeIds.has(parentId)) {
            edges.push(`${parentId} --> ${childId}`);
          }
        });
      });

      return `flowchart LR\n${nodes.join('\n')}\n${edges.join('\n')}`;
    };

    const renderGraph = async () => {
      try {
        const graphDefinition = generateMermaid();
        const id = 'mermaid-' + Date.now();
        const { svg } = await mermaid.render(id, graphDefinition);
        
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = svg;
        }
        setError(null);
      } catch (e) {
        console.error('Mermaid error:', e);
        setError(e instanceof Error ? e.message : 'Failed to render graph');
      }
    };

    renderGraph();
  }, [workflow, context, theme]);

  if (!workflow || !workflow.steps.length) {
    return <div className="loading">No steps in workflow</div>;
  }

  return (
    <div className="graph-view">
      <div className="viewer-header">
        <h2>📊 Workflow Graph</h2>
        <div className="legend">
          {Object.entries(SCOPE_COLORS).map(([scope, color]) => (
            <span key={scope} className="legend-item">
              <span className="legend-color" style={{ background: color }} />
              {scope}
            </span>
          ))}
          <span className="legend-item">
            <span className="legend-color" style={{ background: 'var(--bg-tertiary)', border: '1px dashed var(--border-color)' }} />
            inactive
          </span>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="graph-container">
        <div ref={mermaidRef} className="mermaid" />
      </div>

      <div className="form-section">
        <h3>Steps</h3>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Folder</th>
                <th>Type</th>
                <th>Scope</th>
                <th>Context</th>
                <th>Dependencies</th>
              </tr>
            </thead>
            <tbody>
              {workflow.steps.map((step) => {
                const isActive = context === 'all' || step.context === context || step.context === 'all';
                return (
                  <tr 
                    key={step.full_name}
                    className="clickable-row"
                    onClick={() => onStepClick(step)}
                    style={{ opacity: isActive ? 1 : 0.5 }}
                  >
                    <td>{step.name}</td>
                    <td>{step.folder}</td>
                    <td>{step.step_type}</td>
                    <td>
                      <span 
                        className="badge"
                        style={{ background: SCOPE_COLORS[step.step_scope] || '#6c757d' }}
                      >
                        {step.step_scope}
                      </span>
                    </td>
                    <td>{step.context}</td>
                    <td>{step.dependencies.length}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <style>{`
        .legend {
          display: flex;
          gap: 15px;
          font-size: 12px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 5px;
        }
        .legend-color {
          width: 12px;
          height: 12px;
          border-radius: 2px;
        }
      `}</style>
    </div>
  );
}
