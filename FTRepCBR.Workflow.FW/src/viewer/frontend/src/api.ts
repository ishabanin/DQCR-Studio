import { TreeNode, ProjectInfo, WorkflowModel, ValidationReport } from './types';

export async function loadProject(path: string): Promise<ProjectInfo> {
  const response = await fetch('/api/project/load', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to load project');
  }
  return response.json();
}

export async function getProjectTree(projectPath: string, modelName?: string): Promise<TreeNode> {
  const params = new URLSearchParams({ project_path: projectPath });
  if (modelName) params.append('model_name', modelName);
  
  const response = await fetch(`/api/project/tree?${params}`);
  if (!response.ok) {
    throw new Error('Failed to get project tree');
  }
  return response.json();
}

export async function getConfig(projectPath: string, type: string, path: string): Promise<any> {
  const params = new URLSearchParams({ project_path: projectPath, type, path });
  const response = await fetch(`/api/config?${params}`);
  if (!response.ok) throw new Error(`Failed to get ${type} config`);
  return response.json();
}

export async function buildWorkflow(
  projectPath: string, 
  modelName: string, 
  context?: string
): Promise<WorkflowModel> {
  const response = await fetch('/api/workflow', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_path: projectPath, model_name: modelName, context })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to build workflow');
  }
  return response.json();
}

export async function getMaterializations(): Promise<string[]> {
  const response = await fetch('/api/materializations');
  if (!response.ok) throw new Error('Failed to get materializations');
  return response.json();
}

export async function getSqlFile(path: string): Promise<{content: string, path: string}> {
  const params = new URLSearchParams({ path });
  const response = await fetch(`/api/sql?${params}`);
  if (!response.ok) throw new Error('Failed to get SQL file');
  return response.json();
}

export async function validateWorkflow(
  projectPath: string, 
  modelName: string, 
  context?: string
): Promise<ValidationReport> {
  const response = await fetch('/api/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_path: projectPath, model_name: modelName, context })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to validate workflow');
  }
  return response.json();
}
