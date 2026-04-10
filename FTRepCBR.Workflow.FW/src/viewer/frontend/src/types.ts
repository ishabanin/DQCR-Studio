export interface ValidationCounts {
  errors: number;
  warnings: number;
  infos: number;
}

export interface TreeNode {
  name: string;
  path: string;
  type: 'project' | 'folder' | 'config' | 'sql' | 'graph';
  configType?: 'project' | 'model' | 'folder' | 'context' | 'parameter';
  children?: TreeNode[];
  validationCounts?: ValidationCounts;
}

export interface ProjectInfo {
  project_name: string;
  models: string[];
  contexts: string[];
}

export interface WorkflowStep {
  step_id: string;
  name: string;
  folder: string;
  full_name: string;
  step_type: string;
  step_scope: string;
  sql_model: SqlModel | null;
  param_model: ParamModel | null;
  dependencies: string[];
  context: string;
  is_ephemeral: boolean;
  enabled: boolean;
  asynch: boolean;
  tools: string[] | null;
}

export interface SqlModel {
  name: string;
  path: string;
  source_sql: string;
  prepared_sql: Record<string, string>;
  rendered_sql: Record<string, string>;
  metadata: SqlMetadata;
  materialization: string;
  context: string;
  attributes?: Attribute[];
  cte_materialization?: any;
  cte_config?: any;
  cte_table_names?: Record<string, string>;
  target_table?: string;
}

export interface SqlMetadata {
  attributes: Attribute[];
  ctes: Record<string, any>;
  parameters?: string[];
  tables?: Record<string, TableInfo>;
  aliases?: AliasInfo[];
  functions?: string[];
  model_refs?: Record<string, any>;
  workflow_refs?: Record<string, any>;
  inline_query_config?: any;
  inline_cte_configs?: Record<string, any>;
  inline_attr_configs?: Record<string, any>;
}

export interface TableInfo {
  alias: string;
  is_variable: boolean;
  is_cte: boolean;
}

export interface AliasInfo {
  alias: string;
  source: string;
  expression: string;
}

export interface Attribute {
  name: string;
  domain_type?: string;
  required?: boolean;
  default_value?: string;
  constraints?: string[];
}

export interface ParamModel {
  name: string;
  domain_type?: string;
  values: Record<string, any>;
}

export interface WorkflowModel {
  model_name: string;
  target_table: TargetTable;
  steps: WorkflowStep[];
  config: WorkflowConfig | null;
  contexts: string[];
  project_contexts?: string[];
}

export interface TargetTable {
  name: string;
  schema: string;
  attributes: Attribute[];
}

export interface WorkflowConfig {
  description: string;
  folders: Record<string, FolderConfig>;
  pre: string[];
  post: string[];
}

export interface FolderConfig {
  materialized: string | null;
  queries: Record<string, QueryConfig>;
  enabled: Record<string, any> | null;
  description: string;
  pre: string[];
  post: string[];
}

export interface QueryConfig {
  materialized: string | null;
  enabled: Record<string, any> | null;
  attributes: Attribute[];
}

export type SelectedItem = {
  type: 'project' | 'model' | 'folder' | 'context' | 'parameter' | 'sql' | 'graph';
  path: string;
} | null;

export type ValidationLevel = 'info' | 'warning' | 'error';

export interface ValidationIssue {
  level: ValidationLevel;
  rule: string;
  category: string;
  message: string;
  location?: string;
  details: Record<string, any>;
}

export interface ValidationReport {
  project_name: string;
  model_name: string;
  template_name: string;
  validation_categories: string[];
  timestamp: string;
  summary: {
    total: number;
    errors: number;
    warnings: number;
    info: number;
  };
  issues: ValidationIssue[];
  template_issues: ValidationIssue[];
}
