import { useState, useCallback, useEffect, useRef } from 'react';
import { ProjectTree } from './components/Sidebar/ProjectTree';
import { ConfigViewer } from './components/Content/ConfigViewer/ConfigViewer';
import { GraphView } from './components/Content/GraphView';
import { SqlViewer } from './components/Content/SqlViewer';
import { loadProject, getProjectTree, buildWorkflow, validateWorkflow } from './api';
import { TreeNode, ProjectInfo, WorkflowModel, SelectedItem, WorkflowStep, ValidationReport } from './types';
import { getDefaultIcon, getIconFileName } from './components/Icons';
import 'prismjs/themes/prism.css';
import './App.css';

const THEME_KEY = 'fw-viewer-theme';

function getInitialTheme(): boolean {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored !== null) return stored === 'light';
  return false;
}

function ThemeToggle({ isDark, onToggle }: { isDark: boolean; onToggle: () => void }) {
  return (
    <button 
      className="theme-toggle" 
      onClick={onToggle}
      title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {isDark ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="5"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
    </button>
  );
}

interface OpenTab {
  id: string;
  item: SelectedItem;
  step?: WorkflowStep;
}

type TabIconType = 'folder' | 'sql' | 'config' | 'parameter' | 'context' | 'model' | 'graph' | 'target';

function getTabIconType(item: SelectedItem): TabIconType {
  if (!item) return 'folder';
  if (item.type === 'sql') return 'sql';
  if (item.type === 'graph') return 'graph';
  if (item.type === 'parameter') return 'parameter';
  if (item.type === 'context') return 'context';
  if (item.type === 'model') return 'model';
  if (item.type === 'project') return 'config';
  if (item.type === 'folder') return 'folder';
  return 'folder';
}

function checkIconExists(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

function TabIcon({ item }: { item: SelectedItem }) {
  const [iconSrc, setIconSrc] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  
  useEffect(() => {
    const iconType = getTabIconType(item);
    const fileName = getIconFileName(iconType);
    
    checkIconExists(fileName).then(exists => {
      if (exists) {
        setIconSrc(fileName);
      }
      setChecked(true);
    });
  }, [item]);

  const iconType = getTabIconType(item);

  if (!checked) {
    return <span className={`tab-icon ${iconType}`}></span>;
  }

  if (iconSrc) {
    return (
      <span className={`tab-icon ${iconType}`}>
        <img src={iconSrc} alt="" className="icon-img" />
      </span>
    );
  }

  return (
    <span className={`tab-icon ${iconType}`}>
      <span className="icon-emoji">{getDefaultIcon(iconType)}</span>
    </span>
  );
}

export function App() {
  const [isDarkMode, setIsDarkMode] = useState(getInitialTheme);
  const [projectPath, setProjectPath] = useState<string>('');
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedContext, setSelectedContext] = useState<string>('all');
  const [projectTree, setProjectTree] = useState<TreeNode | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowModel | null>(null);
  const [selectedItem, setSelectedItem] = useState<SelectedItem>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [isResizing, setIsResizing] = useState(false);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    localStorage.setItem(THEME_KEY, isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const toggleTheme = useCallback(() => {
    setIsDarkMode(prev => !prev);
  }, []);

  const findStepByRelativePath = useCallback((relativePath: string): WorkflowStep | undefined => {
    if (!workflow) return undefined;
    const normalizedPath = relativePath.replace(/\\/g, '/').toLowerCase();
    const fileName = normalizedPath.split('/').pop()?.replace('.sql', '') || '';
    
    return workflow.steps.find(step => {
      if (!step.sql_model?.path) return false;
      const stepPath = step.sql_model.path.replace(/\\/g, '/').toLowerCase();
      const stepFileName = stepPath.split('/').pop()?.replace('.sql', '') || '';
      return stepFileName === fileName && stepPath.includes(normalizedPath.split('/').slice(-2, -1)[0] || '');
    });
  }, [workflow]);

  const openInNewTab = useCallback((item: SelectedItem, step?: WorkflowStep) => {
    if (!item) return;
    const tabId = item.type === 'sql' && step 
      ? `sql-${step.step_id}` 
      : `${item.type}-${item.path}`;
    
    const existingTab = openTabs.find(t => t.id === tabId);
    if (existingTab) {
      setActiveTabId(tabId);
      return;
    }
    
    const newTab: OpenTab = { id: tabId, item, step };
    setOpenTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
  }, [openTabs]);

  const closeTab = useCallback((tabId: string) => {
    setOpenTabs(prev => {
      const newTabs = prev.filter(t => t.id !== tabId);
      if (activeTabId === tabId) {
        setActiveTabId(newTabs.length > 0 ? newTabs[newTabs.length - 1].id : null);
      }
      return newTabs;
    });
  }, [activeTabId]);

  const handleProjectSelect = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    setProjectPath(path);
    setOpenTabs([]);
    setActiveTabId(null);
    
    try {
      const info = await loadProject(path);
      setProjectInfo(info);
      
      if (info.models.length > 0) {
        setSelectedModel(info.models[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (projectPath && selectedModel) {
      getProjectTree(projectPath, selectedModel)
        .then(setProjectTree)
        .catch(console.error);
    }
  }, [projectPath, selectedModel]);

  useEffect(() => {
    if (projectPath && selectedModel) {
      const context = selectedContext === 'all' ? undefined : selectedContext;
      buildWorkflow(projectPath, selectedModel, context)
        .then(setWorkflow)
        .catch(console.error);
    }
  }, [projectPath, selectedModel, selectedContext]);

  useEffect(() => {
    if (!workflow || openTabs.length === 0) return;
    
    openTabs.forEach(tab => {
      if (tab.item?.type === 'sql' && !tab.step) {
        const step = findStepByRelativePath(tab.item.path);
        
        if (step) {
          console.log('Found step for existing tab:', step.name);
          setOpenTabs(prev => prev.map(t => 
            t.id === tab.id ? { ...t, step } : t
          ));
        }
      }
    });
  }, [workflow, openTabs, findStepByRelativePath]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = Math.max(200, Math.min(600, e.clientX));
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  const handleTreeSelect = useCallback((item: SelectedItem) => {
    setSelectedItem(item);
    
    if (!item) return;
    
    if (item.type === 'sql') {
      let step: WorkflowStep | undefined;
      
      if (workflow) {
        step = findStepByRelativePath(item.path);
      }
      
      openInNewTab(item, step);
      return;
    }
    
    openInNewTab(item);
  }, [workflow, openInNewTab, setSelectedItem]);

  const handleVerify = useCallback(async () => {
    if (!projectPath || !selectedModel) return;
    setIsLoading(true);
    setError(null);
    try {
      const context = selectedContext === 'all' ? undefined : selectedContext;
      const report = await validateWorkflow(projectPath, selectedModel, context);
      setValidationReport(report);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to validate project');
    } finally {
      setIsLoading(false);
    }
  }, [projectPath, selectedModel, selectedContext]);

  const applyValidationToTree = useCallback((tree: TreeNode, report: ValidationReport | null): TreeNode => {
    if (!report) return tree;

    const allIssues = [...report.issues, ...report.template_issues];

    const normalizePath = (path: string): string => {
      return path.replace(/\\/g, '/').toLowerCase();
    };

    const matchesLocation = (nodePath: string, location: string | undefined): boolean => {
      if (!location) return false;
      
      const normalizedNodePath = normalizePath(nodePath);
      const normalizedLocation = normalizePath(location);
      
      if (normalizedNodePath.endsWith(normalizedLocation)) return true;
      if (normalizedLocation.endsWith(normalizedNodePath)) return true;
      
      const nodeParts = normalizedNodePath.split('/');
      const locationParts = normalizedLocation.split('/');
      const nodeFileName = nodeParts[nodeParts.length - 1];
      const locationFileName = locationParts[locationParts.length - 1];
      
      if (nodeFileName === locationFileName) return true;
      
      return false;
    };

    const processNode = (node: TreeNode): TreeNode => {
      let errors = 0;
      let warnings = 0;
      let infos = 0;

      for (const issue of allIssues) {
        if (matchesLocation(node.path, issue.location)) {
          if (issue.level === 'error') errors++;
          else if (issue.level === 'warning') warnings++;
          else infos++;
        }
      }

      let finalCounts = { errors, warnings, infos };

      if (node.children) {
        const processedChildren = node.children.map(processNode);
        const childCounts = processedChildren.reduce(
          (acc, child) => ({
            errors: acc.errors + (child.validationCounts?.errors || 0),
            warnings: acc.warnings + (child.validationCounts?.warnings || 0),
            infos: acc.infos + (child.validationCounts?.infos || 0),
          }),
          { errors: 0, warnings: 0, infos: 0 }
        );

        finalCounts = {
          errors: finalCounts.errors + childCounts.errors,
          warnings: finalCounts.warnings + childCounts.warnings,
          infos: finalCounts.infos + childCounts.infos,
        };

        return {
          ...node,
          children: processedChildren,
          validationCounts: finalCounts,
        };
      }

      return {
        ...node,
        validationCounts: finalCounts,
      };
    };

    return processNode(tree);
  }, []);

  const renderTabContent = (tab: OpenTab) => {
    const { item, step } = tab;
    if (!item) return null;
    
    if (item.type === 'sql' && step?.sql_model) {
      return (
        <SqlViewer
          sql={step.sql_model}
          name={step.name}
          folder={step.folder}
          dependencies={step.dependencies}
          projectContexts={workflow?.project_contexts}
          onParamClick={(paramName) => {
            const paramStep = workflow?.steps.find(s => 
              s.param_model && s.full_name?.toLowerCase().includes(paramName.toLowerCase())
            );
            if (paramStep?.param_model && workflow) {
              const paramPath = `model/${workflow.model_name}/parameters/${paramStep.param_model.name}.yml`;
              const newItem: SelectedItem = { 
                type: 'parameter', 
                path: paramPath
              };
              openInNewTab(newItem);
            }
          }}
          onTableClick={(tableName) => {
            console.log('Table clicked:', tableName);
          }}
        />
      );
    }
    
    if (item.type === 'sql' && !step) {
      const fileName = item.path.split(/[/\\]/).pop() || 'SQL';
      return (
        <SqlViewer
          sourceFilePath={item.path}
          name={fileName}
        />
      );
    }
    
    if (item.type === 'graph' && workflow) {
      return (
        <GraphView 
          workflow={workflow} 
          context={selectedContext}
          onStepClick={(step) => {
            if (step.sql_model) {
              const sqlPath = `${workflow.model_name}/SQL/${step.folder}/${step.name}.sql`;
              openInNewTab({ type: 'sql', path: sqlPath }, step);
            }
          }}
        />
      );
    }
    
    return (
      <ConfigViewer
        item={item}
        projectPath={projectPath}
        workflow={workflow}
      />
    );
  };

  const getTabLabel = (tab: OpenTab): string => {
    if (!tab.item) return 'Unknown';
    
    if (tab.item.type === 'sql' && tab.step) {
      return tab.step.name;
    }
    if (tab.item.type === 'sql') {
      const fileName = tab.item.path.split(/[/\\]/).pop() || 'SQL';
      return fileName.replace('.sql', '');
    }
    if (tab.item.type === 'graph') {
      return 'Graph';
    }
    if (tab.item.type === 'project') {
      return 'Project';
    }
    
    const fileName = tab.item.path.split(/[/\\]/).pop() || '';
    return fileName.replace('.yml', '');
  };

  const renderContent = () => {
    if (!projectPath) {
      return (
        <div className="welcome">
          <h2>FW Workflow Viewer</h2>
          <p>Select a project folder to get started</p>
          <input
            type="file"
            // @ts-expect-error - webkitdirectory is not in standard types
            webkitdirectory=""
            onChange={(e) => {
              const files = e.target.files;
              if (files && files.length > 0) {
                const path = files[0].webkitRelativePath.split('/')[0];
                handleProjectSelect(path);
              }
            }}
          />
        </div>
      );
    }

    if (openTabs.length > 0) {
      return (
        <div className="tabs-container">
          <div className="tabs-header">
            {openTabs.map(tab => (
              <div 
                key={tab.id} 
                className={`tab ${activeTabId === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTabId(tab.id)}
              >
                <TabIcon item={tab.item} />
                <span className="tab-label">{getTabLabel(tab)}</span>
                <button 
                  className="tab-close"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tab.id);
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className="tab-content">
            {activeTabId && renderTabContent(openTabs.find(t => t.id === activeTabId)!)}
          </div>
        </div>
      );
    }

    return (
      <div className="empty-content">
        <p>Select an item from the tree to view details</p>
      </div>
    );
  };

  return (
    <div className="app">
      <div className="toolbar">
        <div className="toolbar-section">
          <label>Project:</label>
          <input
            type="text"
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
            placeholder="Path to project"
            className="path-input"
          />
          <button onClick={() => projectPath && handleProjectSelect(projectPath)}>
            Load
          </button>
          <button onClick={handleVerify} disabled={!projectPath || !selectedModel || isLoading}>
            Verify
          </button>
        </div>
        
        {projectInfo && (
          <>
            <div className="toolbar-section">
              <label>Model:</label>
              <select 
                value={selectedModel} 
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {projectInfo.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            
            <div className="toolbar-section">
              <label>Context:</label>
              <select 
                value={selectedContext} 
                onChange={(e) => setSelectedContext(e.target.value)}
              >
                <option value="all">all</option>
                {projectInfo.contexts.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </>
        )}

        <div className="toolbar-spacer" />

        <ThemeToggle isDark={isDarkMode} onToggle={toggleTheme} />
      </div>

      <div className="main-content">
        <div className="sidebar" ref={sidebarRef} style={{ width: sidebarWidth }}>
          {projectTree && (
            <ProjectTree 
              tree={applyValidationToTree(projectTree, validationReport)} 
              onSelect={handleTreeSelect}
              selectedItem={selectedItem}
              projectPath={projectPath}
              workflow={workflow}
            />
          )}
        </div>
        <div 
          className="sidebar-resizer"
          onMouseDown={() => setIsResizing(true)}
        />
        
        <div className="content">
          {error && <div className="error">{error}</div>}
          {isLoading ? <div className="loading">Loading...</div> : renderContent()}
        </div>
      </div>
    </div>
  );
}

export default App;
