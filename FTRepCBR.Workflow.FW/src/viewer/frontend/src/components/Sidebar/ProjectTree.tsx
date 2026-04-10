import React, { useState, useCallback } from 'react';
import { TreeNode, SelectedItem, WorkflowModel, ValidationCounts } from '../../types';
import { getDefaultIcon, getIconFileName } from '../Icons';

interface ProjectTreeProps {
  tree: TreeNode;
  onSelect: (item: SelectedItem) => void;
  selectedItem: SelectedItem;
  projectPath: string;
  workflow?: WorkflowModel | null;
}

type IconType = 'folder' | 'folder_open' | 'sql' | 'config' | 'parameter' | 'context' | 'model' | 'graph' | 'target';

function getNodeIconType(node: TreeNode): IconType {
  if (node.type === 'folder') return 'folder';
  if (node.type === 'graph') return 'graph';
  if (node.type === 'sql') return 'sql';
  if (node.type === 'config') {
    switch (node.configType) {
      case 'parameter': return 'parameter';
      case 'context': return 'context';
      case 'model': return 'model';
      default: return 'config';
    }
  }
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

function TreeIcon({ node, isFolder, isExpanded, validationCounts }: { node: TreeNode; isFolder: boolean; isExpanded: boolean; validationCounts?: ValidationCounts }) {
  const [iconSrc, setIconSrc] = useState<string | null>(null);
  const [openIconSrc, setOpenIconSrc] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  
  React.useEffect(() => {
    const iconType = getNodeIconType(node);
    
    async function loadIcons() {
      if (isFolder) {
        const closedFile = getIconFileName('folder');
        const openFile = getIconFileName('folder_open');
        
        const closedExists = await checkIconExists(closedFile);
        if (closedExists) {
          setIconSrc(closedFile);
        }
        
        const openExists = await checkIconExists(openFile);
        if (openExists) {
          setOpenIconSrc(openFile);
        }
      } else {
        const fileName = getIconFileName(iconType);
        const exists = await checkIconExists(fileName);
        if (exists) {
          setIconSrc(fileName);
        }
      }
      setChecked(true);
    }
    
    loadIcons();
  }, [node, isFolder]);

  const iconType = getNodeIconType(node);
  
  const hasValidationIssues = validationCounts && (
    validationCounts.errors > 0 || 
    validationCounts.warnings > 0 || 
    validationCounts.infos > 0
  );

  const renderBadges = () => {
    if (!hasValidationIssues) return null;
    
    return (
      <>
        {validationCounts!.errors > 0 && (
          <img 
            className="icon-badge error" 
            src="/icons/error.svg" 
            alt="errors"
            title={`Errors: ${validationCounts!.errors}`}
            style={{ position: 'absolute', bottom: -2, left: -2, width: 8, height: 8, border: 'none', padding: 0, margin: 0 }}
          />
        )}
        {validationCounts!.warnings > 0 && (
          <img 
            className="icon-badge warning" 
            src="/icons/warning.svg" 
            alt="warnings"
            title={`Warnings: ${validationCounts!.warnings}`}
            style={{ position: 'absolute', top: -2, left: -2, width: 8, height: 8, border: 'none', padding: 0, margin: 0 }}
          />
        )}
        {validationCounts!.infos > 0 && (
          <img 
            className="icon-badge info" 
            src="/icons/info.svg" 
            alt="info"
            title={`Info: ${validationCounts!.infos}`}
            style={{ position: 'absolute', bottom: -2, right: -2, width: 8, height: 8, border: 'none', padding: 0, margin: 0 }}
          />
        )}
      </>
    );
  };

  if (isFolder) {
    const currentSrc = isExpanded ? (openIconSrc || iconSrc) : iconSrc;
    const fallbackEmoji = isExpanded ? '📂' : '📁';
    
    return (
      <span className="tree-icon-wrapper" style={{ position: 'relative', display: 'inline-flex', width: 20, height: 20, flexShrink: 0 }}>
        <span className="tree-icon folder">
          {checked && currentSrc ? (
            <img src={currentSrc} alt="" className="icon-img" />
          ) : (
            <span className="icon-emoji">{fallbackEmoji}</span>
          )}
        </span>
        {renderBadges()}
      </span>
    );
  }

  if (!checked) {
    return (
      <span className="tree-icon-wrapper" style={{ position: 'relative', display: 'inline-flex', width: 20, height: 20, flexShrink: 0 }}>
        <span className={`tree-icon ${iconType}`}></span>
        {renderBadges()}
      </span>
    );
  }

  if (iconSrc) {
    return (
      <span className="tree-icon-wrapper" style={{ position: 'relative', display: 'inline-flex', width: 20, height: 20, flexShrink: 0 }}>
        <span className={`tree-icon ${iconType}`}>
          <img src={iconSrc} alt="" className="icon-img" />
        </span>
        {renderBadges()}
      </span>
    );
  }

  return (
    <span className="tree-icon-wrapper" style={{ position: 'relative', display: 'inline-flex', width: 20, height: 20, flexShrink: 0 }}>
      <span className={`tree-icon ${iconType}`}>
        <span className="icon-emoji">{getDefaultIcon(iconType)}</span>
      </span>
      {renderBadges()}
    </span>
  );
}

function getNodeContexts(node: TreeNode, workflow: WorkflowModel | null | undefined): string[] | null {
  if (!workflow?.steps) return null;
  
  const { steps } = workflow;
  
  const isConfigFile = node.configType === 'context' || 
                       node.configType === 'project' || 
                       node.configType === 'folder' || 
                       node.configType === 'parameter';
  if (isConfigFile) return null;

  let matchingContexts: string[] = [];
  let allStepsHaveAllContext = true;
  let hasAnyStep = false;

  if (node.type === 'project' || node.configType === 'model') {
    const seen = new Set<string>();
    for (const step of steps) {
      hasAnyStep = true;
      if (step.context) {
        if (!seen.has(step.context)) {
          seen.add(step.context);
          matchingContexts.push(step.context);
        }
        if (step.context !== 'all') {
          allStepsHaveAllContext = false;
        }
      }
    }
  }
  else if (node.type === 'sql') {
    const sqlFileName = node.name.toLowerCase().replace('.sql', '').replace('.SQL', '');
    const folderPathParts = node.path.split(/[/\\]/);
    const folderName = folderPathParts[folderPathParts.length - 2] || '';
    
    const seen = new Set<string>();
    for (const step of steps) {
      if (step.step_type !== 'sql') continue;
      
      const stepFileName = (step.name || step.sql_model?.name || '').toLowerCase().replace('.sql', '').replace('.SQL', '');
      const stepFolder = step.folder || '';
      
      const nameMatches = stepFileName === sqlFileName;
      const folderMatches = stepFolder === folderName || stepFolder.toLowerCase() === folderName.toLowerCase();
      
      if (nameMatches && (folderMatches || folderName === '')) {
        hasAnyStep = true;
        if (step.context) {
          if (!seen.has(step.context)) {
            seen.add(step.context);
            matchingContexts.push(step.context);
          }
          if (step.context !== 'all') {
            allStepsHaveAllContext = false;
          }
        }
      }
    }
  }
  else if (node.type === 'folder') {
    if (node.name === 'SQL' || node.name === 'parameters') {
      const seen = new Set<string>();
      for (const step of steps) {
        hasAnyStep = true;
        if (step.context) {
          if (!seen.has(step.context)) {
            seen.add(step.context);
            matchingContexts.push(step.context);
          }
          if (step.context !== 'all') {
            allStepsHaveAllContext = false;
          }
        }
      }
    } else {
      const seen = new Set<string>();
      for (const step of steps) {
        if (step.folder === node.name && step.context) {
          hasAnyStep = true;
          if (!seen.has(step.context)) {
            seen.add(step.context);
            matchingContexts.push(step.context);
          }
          if (step.context !== 'all') {
            allStepsHaveAllContext = false;
          }
        }
      }
    }
  }
  else if (node.configType === 'folder') {
    const folderName = node.name === 'folder.yml' 
      ? node.path.split(/[/\\]/).slice(-2, -1)[0]
      : node.name;
    const seen = new Set<string>();
    for (const step of steps) {
      if (step.folder === folderName && step.context) {
        hasAnyStep = true;
        if (!seen.has(step.context)) {
          seen.add(step.context);
          matchingContexts.push(step.context);
        }
        if (step.context !== 'all') {
          allStepsHaveAllContext = false;
        }
      }
    }
  }
  else if (node.configType === 'parameter') {
    const paramName = (node.name.replace('.yml', '') || '').toLowerCase();
    const seen = new Set<string>();
    for (const step of steps) {
      if (step.param_model?.name?.toLowerCase() === paramName && step.context) {
        hasAnyStep = true;
        if (!seen.has(step.context)) {
          seen.add(step.context);
          matchingContexts.push(step.context);
        }
        if (step.context !== 'all') {
          allStepsHaveAllContext = false;
        }
      }
    }
  }

  if (!hasAnyStep || matchingContexts.length === 0) return null;

  const filteredContexts = matchingContexts.filter(c => c !== 'all');
  
  if (filteredContexts.length === 0) {
    return allStepsHaveAllContext ? ['all'] : null;
  }
  
  if (allStepsHaveAllContext) {
    return ['all'];
  }

  return filteredContexts.sort();
}

export function ProjectTree({ tree, onSelect, selectedItem, workflow }: ProjectTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set([tree.path]));

  const toggle = useCallback((path: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback((node: TreeNode) => {
    if (node.type === 'graph') {
      onSelect({ type: 'graph', path: '__graph__' });
      return;
    }
    
    const itemType = (node.configType || node.type) as 'project' | 'model' | 'folder' | 'context' | 'parameter' | 'sql';
    onSelect({ type: itemType, path: node.path });
  }, [onSelect]);

  const isSelected = (node: TreeNode): boolean => {
    if (!selectedItem) return false;
    return selectedItem.path === node.path;
  };

  const renderNode = (node: TreeNode, level: number = 0): React.ReactNode => {
    const isFolder = node.type === 'folder' || node.type === 'project';
    const isExpanded = expanded.has(node.path);
    const contexts = getNodeContexts(node, workflow);

    return (
      <div key={node.path} className="tree-node">
        <div 
          className={`tree-node-header ${isSelected(node) ? 'selected' : ''}`}
          style={{ paddingLeft: `${10 + level * 15}px` }}
          onClick={() => {
            if (isFolder) {
              toggle(node.path);
            }
            handleSelect(node);
          }}
        >
          <TreeIcon node={node} isFolder={isFolder} isExpanded={isExpanded} validationCounts={node.validationCounts} />
          <span style={{ flexShrink: 0 }}>{node.name}</span>
          {contexts && contexts.length > 0 && (
            <div className="tree-context-badges">
              {contexts.map(ctx => (
                <span key={ctx} className="tree-context-badge">{ctx}</span>
              ))}
            </div>
          )}
        </div>
        {isFolder && isExpanded && node.children && (
          <div className="tree-children">
            {node.children.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="project-tree">
      {renderNode(tree)}
    </div>
  );
}
