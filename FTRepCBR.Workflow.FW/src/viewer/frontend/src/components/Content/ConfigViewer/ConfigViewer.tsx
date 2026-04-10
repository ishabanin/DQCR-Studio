import { useState, useEffect } from 'react';
import { SelectedItem, WorkflowModel } from '../../../types';
import { getConfig, getMaterializations } from '../../../api';
import { YamlViewer } from './YamlViewer';
import { TypeIcon } from '../../TypeIcon';

interface ConfigViewerProps {
  item: SelectedItem;
  projectPath: string;
  workflow: WorkflowModel | null;
}

type ViewMode = 'form' | 'yaml';

function getDisplayName(item: SelectedItem): string {
  if (!item || !item.path) return '';
  
  const parts = item.path.split(/[/\\]/);
  const fileName = parts[parts.length - 1];
  
  if (item.type === 'project') return 'Project';
  if (item.type === 'context') return fileName.replace('.yml', '');
  if (item.type === 'parameter') return fileName.replace('.yml', '');
  if (item.type === 'model') return parts.length >= 2 ? parts[parts.length - 2] : fileName;
  if (item.type === 'folder') return parts.length >= 2 ? parts[parts.length - 2] : fileName;
  return fileName;
}

export function ConfigViewer({ item, projectPath }: ConfigViewerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('form');
  const [configData, setConfigData] = useState<any>(null);
  const [materializations, setMaterializations] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getMaterializations().then(setMaterializations).catch(console.error);
  }, []);

  useEffect(() => {
    if (!projectPath || !item || !item.path) return;
    
    setLoading(true);
    const loadConfig = async () => {
      try {
        const data = await getConfig(projectPath, item.type, item.path);
        setConfigData(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    
    loadConfig();
  }, [item, projectPath]);

  if (loading || !configData) {
    return <div className="loading">Loading config...</div>;
  }

  const renderProjectConfig = () => (
    <div className="form-section">
      <h3>Project Settings</h3>
      <div className="form-grid">
        <label>Name:</label>
        <span>{configData.name || '-'}</span>
        
        <label>Description:</label>
        <span>{configData.description || '-'}</span>
        
        <label>Template:</label>
        <span>{configData.template || '-'}</span>
        
        <label>Properties:</label>
        <span>{JSON.stringify(configData.properties || {})}</span>
      </div>
    </div>
  );

  const renderModelConfig = () => {
    const targetTable = configData.target_table;
    const workflow = configData.workflow;
    
    const workflowPre = Array.isArray(workflow?.pre) ? workflow.pre.join(', ') : '-';
    const workflowPost = Array.isArray(workflow?.post) ? workflow.post.join(', ') : '-';
    
    return (
      <>
        {targetTable && (
          <div className="form-section">
            <h3>Target Table</h3>
            <div className="form-grid">
              <label>Name:</label>
              <span>{targetTable.name}</span>
              
              <label>Schema:</label>
              <span>{targetTable.schema}</span>
            </div>
            
            {targetTable.attributes && (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Domain Type</th>
                      <th>Required</th>
                      <th>Default</th>
                      <th>Constraints</th>
                      <th>Dist</th>
                      <th>Part</th>
                    </tr>
                  </thead>
                  <tbody>
                    {targetTable.attributes.map((attr: any, i: number) => (
                      <tr key={i}>
                        <td>{attr.name}</td>
                        <td><TypeIcon domainType={attr.domain_type} /></td>
                        <td>{attr.required ? '✓' : ''}</td>
                        <td>{attr.default_value || '-'}</td>
                        <td>{attr.constraints?.join(', ') || '-'}</td>
                        <td>{attr.distribution_key !== undefined && attr.distribution_key !== null ? attr.distribution_key : ''}</td>
                        <td>{attr.partition_key !== undefined && attr.partition_key !== null ? attr.partition_key : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        
        {workflow && (
          <div className="form-section">
            <h3>Workflow</h3>
            <div className="form-grid">
              <label>Description:</label>
              <span>{workflow.description || '-'}</span>
              
              <label>Pre:</label>
              <span>{workflowPre}</span>
              
              <label>Post:</label>
              <span>{workflowPost}</span>
            </div>
            
            {workflow.folders && (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Folder</th>
                      <th>Materialized</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(workflow.folders).map(([name, cfg]: [string, any]) => (
                      <tr key={name}>
                        <td>{name}</td>
                        <td>{cfg.materialized || '-'}</td>
                        <td>{cfg.description || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </>
    );
  };

  const renderFolderConfig = () => {
    if (!item || item.type !== 'folder') return null;
    
    const folderPre = Array.isArray(configData.pre) ? configData.pre.join(', ') : '-';
    const folderPost = Array.isArray(configData.post) ? configData.post.join(', ') : '-';
    
    return (
    <div className="form-section">
      <h3>Folder: {getDisplayName(item)}</h3>
      <div className="form-grid">
        <label>Materialization:</label>
        <select value={configData.materialized || ''} disabled>
          {materializations.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        
        <label>Description:</label>
        <span>{configData.description || '-'}</span>
        
        <label>Pre:</label>
        <span>{folderPre}</span>
        
        <label>Post:</label>
        <span>{folderPost}</span>
      </div>
      
      {configData.queries && (
        <div className="form-section">
          <h3>Queries</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Materialization</th>
                  <th>Enabled</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(configData.queries).map(([name, cfg]: [string, any]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>{cfg.materialized || '-'}</td>
                    <td>{cfg.enabled ? JSON.stringify(cfg.enabled) : '✓'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
    );
  };

  const renderContextConfig = () => {
    if (!item || item.type !== 'context') return null;
    return (
    <div className="form-section">
      <h3>Context: {getDisplayName(item)}</h3>
      {configData && (
        <div className="table-container">
          <table className="param-table">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(configData).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{JSON.stringify(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
    );
  };

  const renderContent = () => {
    if (!item) return <div>Select an item to view</div>;
    if (item.type === 'project') return renderProjectConfig();
    if (item.type === 'model') return renderModelConfig();
    if (item.type === 'folder') return renderFolderConfig();
    if (item.type === 'context') return renderContextConfig();
    return <div>Select an item to view</div>;
  };

  const displayName = getDisplayName(item);
  const title = item?.type === 'project' 
    ? '⚙️ Project Config' 
    : `⚙️ ${item?.type}: ${displayName}`;

  return (
    <div className="config-viewer">
      <div className="viewer-header">
        <h2>{title}</h2>
      </div>
      
      <div className="viewer-tabs">
        <button 
          className={`viewer-tab ${viewMode === 'form' ? 'active' : ''}`}
          onClick={() => setViewMode('form')}
        >
          Form View
        </button>
        <button 
          className={`viewer-tab ${viewMode === 'yaml' ? 'active' : ''}`}
          onClick={() => setViewMode('yaml')}
        >
          YAML
        </button>
      </div>
      
      {viewMode === 'form' ? renderContent() : <YamlViewer data={configData} />}
    </div>
  );
}
