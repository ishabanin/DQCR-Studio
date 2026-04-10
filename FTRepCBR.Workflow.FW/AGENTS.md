# AGENTS.md - Agent Coding Guidelines

## Project Overview
Python project for generating SQL workflows from SQL files. DQCR Framework - dbt-inspired framework for data transformation.

```
FW/                    # Main framework
├── cli.py             # CLI entry point
├── config/            # Tool registry, templates
├── generation/        # Builders, dependency resolver
├── macros/           # Python macros + Jinja2 templates
│   ├── main/         # Base macros (materialization, functions, model_ref)
│   ├── oracle/       # Oracle-specific macros
│   ├── adb/          # ADB-specific macros
│   ├── postgresql/   # PostgreSQL-specific macros
│   └── workflow/     # Workflow engine generators (airflow, dbt, oracle_plsql)
├── materialization/  # SQL renderer
├── models/           # Data models
├── parsing/         # YAML/SQL loaders
└── validation/      # Validation system
    ├── models.py    # ValidationReport, ValidationIssue
    ├── rule_runner.py
    ├── template_validator.py
    ├── html_generator.py
    └── rules/       # Validation rules by category
RF110/               # Test project
RF110NEW/            # Test project with model_ref macros
```

---

## Build / Lint / Test Commands

### Syntax & Type Checking
```bash
python -m py_compile FW/path/to/file.py
```

### Testing
```bash
# All tests
python -m pytest test_cli.py -v

# Single test
python -m pytest test_cli.py::test_function_name -v
```

### FW CLI Commands
```bash
# Build workflow model (JSON output)
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -o output.json
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -c vtb -o output.json

# Generate workflow files for specific engine (workflow_engine MUST be specified)
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg" -w airflow
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg" -w dbt
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg" -w oracle_plsql

# Validate project (new)
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg"
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -c default
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -r "general,sql,adb,descriptions"
python -m FW.cli validate "RF110NEW" -o validation_reports

# Parse SQL to metadata
python -m FW.cli parse-sql "path/to/file.sql" -o metadata.json

# Parse parameter YAML
python -m FW.cli parse-param "path/to/param.yml" -o param.json
```

---

## Code Style Guidelines

### General Principles
- **PEP 8** compliance
- **Russian comments** (project convention)
- **Max 50 lines** per function
- **Docstrings** for classes/public functions (Google style)
- **NO comments** unless explicitly requested

### Imports Order
1. Standard library (`os`, `json`, `re`, `pathlib`, `typing`)
2. Third-party (`yaml`, `jinja2`)
3. Local (`from FW.config import ...`)

### Type Hints
Required for all arguments and return values. Use `Optional[T]` for nullable types.

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `WorkflowStepModel` |
| Functions/methods | snake_case | `render_template` |
| Variables | snake_case | `param_values` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_TOOL` |
| Enum values | UPPER_SNAKE_CASE | `STEP_TYPE_SQL` |

### Error Handling & Logging
```python
from FW.logging_config import get_logger
from FW.exceptions import ConfigValidationError

logger = get_logger("component_name")
logger.info("Loading...")
logger.warning(f"Param not found: {name}")
logger.error(f"Failed to parse: {e}")

# Raise typed exceptions
raise ConfigValidationError("workflow_engine must be specified either in template config or via -w CLI option", field="workflow_engine")
```

### Custom Exceptions
Location: `FW/exceptions/`
- `BaseFWError` - base class
- `ConfigValidationError` - config validation errors (with optional `field` attribute)
- `TemplateNotFoundError` - template not found
- `ModelNotFoundError` - model not found

---

## Framework Architecture

### CLI Entry Point
**File:** `FW/cli.py`
- `parse_sql_command(sql_path, output)` - Parse SQL file to metadata
- `parse_sql_model_command(sql_path, output)` - Parse SQL to SQLQueryModel
- `parse_parameter_command(param_path, output)` - Parse parameter YAML
- `build_command(project_path, model_name, context, output)` - Build workflow model
- `generate_command(project_path, model_name, context, output, workflow_engine)` - Generate workflow files
- `validate_command(project_path, model_name, context, output, categories)` - Validate project

### Generation Module

**BaseBuilder** (`FW/generation/base.py`): Abstract base class
- `build(model_name)` - Build workflow model
- `build_all()` - Build all workflow models

**DefaultBuilder** (`FW/generation/DefaultBuilder.py`): Main builder implementation
- `build(model_name, context_name)` - Build workflow for model
- `build_all(context_name)` - Build all models
- `_build_sql_steps(model_path, target_table, active_context)` - Build SQL steps
- `_build_param_steps(active_context)` - Build parameter steps
- `_create_cte_materialization_steps(...)` - Create materialized CTE steps
- `_resolve_all_model_refs(all_steps, workflow)` - Resolve _m.* and _w.* references
- `_is_folder_enabled(folder)` - Check folder enabled
- `_is_query_enabled(folder, query_name)` - Check query enabled

**DependencyResolver** (`FW/generation/dependency_resolver.py`): Abstract resolver
- `resolve(steps)` - Determine step dependencies

**Resolvers:** `naming_convention.py`, `graph_based.py`, `explicit.py`

---

## Key Models

### WorkflowModel (`FW/models/workflow.py`)
```python
model_name: str           # Model name
graph: WorkflowGraph      # DAG of steps
steps: List[WorkflowStepModel]  # All steps
target_table: TargetTableModel
settings: WorkflowSettings
tools: List[str]
config: WorkflowConfig
```

### WorkflowStepModel (`FW/models/step.py`)
```python
step_id: str             # Unique ID
name: str                # Short name
folder: str               # Folder path
full_name: str           # folder/name
step_type: StepType      # SQL, PARAM, PREHOOK
step_scope: str          # flags, pre, params, sql, post
sql_model: SQLQueryModel
param_model: ParameterModel
dependencies: List[str]   # Step full_names
context: str
is_ephemeral: bool
```

### SQLQueryModel (`FW/models/sql_query.py`)
```python
name: str
path: Path
source_sql: str
metadata: SQLMetadata
materialization: str
context: str
prepared_sql: Dict[str, str]   # tool -> prepared SQL
rendered_sql: Dict[str, str]   # tool -> rendered SQL
attributes: List[Attribute]
cte_config: CTEMaterializationConfig

# Methods
get_prepared_sql(tool) -> str
get_rendered_sql(tool) -> str
get_attribute_names() -> Set[str]
get_key_attributes(target_table) -> List[str]
get_update_attributes(target_table, key_attrs) -> List[str]
```

### ParameterModel (`FW/models/parameter.py`)
```python
name: str
domain_type: str
values: Dict[str, ParameterValue]
prepared_sql: Dict[str, str]
rendered_sql: Dict[str, str]

# Methods
get_value(context) -> Any
get_param_type(context) -> str
is_dynamic(context) -> bool
get_prepared_sql(tool) -> str
get_rendered_sql(tool) -> str
```

### TargetTableModel (`FW/models/target_table.py`)
```python
name: str
schema: str
attributes: List[Attribute]

# Methods
get_attribute(name) -> Optional[Attribute]
find_attributes_in_query(sql_model) -> List[Attribute]
get_key_attributes_for_insert(sql_model) -> List[str]
get_required_attributes_not_in_query(sql_model) -> List[tuple]
```

---

## Macro System

### MacroEnv (`FW/macros/env.py`)
Environment for materialization/model_ref macros:
```python
env.render_template(template_name, tool=tool, **kwargs)
env.workflow           # WorkflowModel
env.tools              # List[str]
env.step               # WorkflowStepModel
env.param_model        # ParameterModel
env.steps              # List[WorkflowStepModel]
env.add_step(step)     # Add step to workflow
env.get_step_by_name(full_name)  # Find step
env.get_all_steps()    # Get all workflow steps
env.get_steps_in_folder(folder)  # Get steps in folder
```

### WorkflowMacroEnv (`FW/macros/env.py`)
Environment for workflow engine generators:
```python
env.target_path              # Path to target/<engine>/<workflow_name>/
env.workflow_name            # Workflow model name
env.create_file(relative_path, content)  # Create file
env.create_directory(name)   # Create subdirectory
env.render_template(template_name, tool=engine, **kwargs)
env.get_all_steps()          # Get all workflow steps
```

### MacroRegistry (`FW/macros/__init__.py`)
```python
get_macro(name, tool) -> str
has_python_macro(name, tool) -> bool
get_python_macro(name, tool) -> Callable
get_model_ref_macro(name, tool) -> Callable
```

---

## Materialization Renderer

**File:** `FW/materialization/renderer.py`

```python
class MaterializationRenderer:
    set_parameters(parameters)
    prepare_sql(sql_model, tool, param_values, workflow, context_name)
    apply_materialization(sql_model, prepared_sql, tool, workflow, step)
    render_sql_query(sql_model, tool, param_values, workflow, step)
    prepare_param(param_model, tool, param_values, context_name)
    render_parameter(param_model, tool, param_values, workflow, context_name, step)
    render_all(sql_model, tools, param_values, workflow, context_name, step)
    render_all_params(param_model, tools, param_values, workflow, context_name, step)
```

---

## Config Registries

**ToolRegistry** (`FW/config/__init__.py`)
```python
tools: List[str]
default_materialization: str
get(name) -> ToolConfig
has_tool(name) -> bool
```

**WorkflowEngineRegistry** (`FW/config/__init__.py`)
```python
engines: List[str]
default: str
get(name) -> WorkflowEngineModel
has_engine(name) -> bool
```

**TemplateRegistry** (`FW/config/__init__.py`)
```python
templates: List[str]
get(name) -> ProjectTemplate
has_template(name) -> bool
```

---

## Important Implementation Notes

1. **No default values** - Framework has no defaults for:
   - `workflow_engine` - must be specified in template or via `-w` CLI
   - `default_materialization` - must be specified in template/model config
   - If not specified, raises `ConfigValidationError`

2. **Graph creation timing** - Graph is created ONCE at end of build, not before macros.
   `MacroEnv.add_step()` adds to env.steps list, not directly to graph.

3. **CTE materialization** - Configured in model.yml via `cte.cte_materialization` with support for:
   - `default`, `by_context`, `by_tool` overrides

4. **Dependency resolution** - Use `naming_convention` (default), `graph_based`, or `explicit`

5. **Workflow passed to macros** - When calling materialization macros, `render_all` receives temporary WorkflowModel. Access via `env.workflow` (not the `workflow` parameter which may be None).

6. **Context handling** - Use `'all'` for "all contexts" (not empty string `''`). Empty context is replaced with `'all'` in builder logic.

---

## Materialization Macros

### Structure
- Python macro (`*.py`) defines logic
- Jinja2 template (`*.sql.j2`) defines SQL output
- Tool-specific templates in `macros/<tool>/materialization/` override main templates

### Python Macro Pattern
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv

def materialization_upsert_fc(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    wf = env.workflow or workflow
    target_table = wf.target_table if wf and wf.target_table else None
    
    for tool in env.tools:
        prepared = step.sql_model.get_prepared_sql(tool)
        rendered = env.render_template(
            "materialization/upsert_fc_body",
            tool=tool,
            target_table=target_table.name if target_table else step.sql_model.target_table,
            sql=prepared
        )
        step.sql_model.rendered_sql[tool] = rendered
```

### Template Search Order
1. `<tool>/materialization/<name>` (e.g., `oracle/materialization/upsert_fc_body.sql.j2`)
2. `main/materialization/<name>` (fallback)

---

## Model Configuration (model.yml)

### Target Table
```yaml
target_table:
  name: RF110RestTurnReg
  schema: RF110
  attributes:
    - name: dealid
      domain_type: number
      is_key: true
      constraints: [PRIMARY_KEY]
```

### Query Attributes
```yaml
workflow:
  folders:
    002_Update:
      queries:
        001_MyQuery:
          attributes:
            - name: clientid
              is_key: true
            - name: clientinn
```

### Attribute Fields
| Field | Description |
|-------|-------------|
| `name` | Attribute name |
| `domain_type` | Type: string, number, date, etc |
| `is_key` | Key attribute for upsert |
| `required` | Required attribute - needs default_value |
| `default_value` | Default value |
| `constraints` | List: PRIMARY_KEY, FOREIGN_KEY, NOT_NULL |

---

## Folder-Level Configuration (folder.yml)

You can define configuration for specific folders in separate `folder.yml` files located inside each SQL folder. This allows you to keep folder-specific settings independent from the main `model.yml`.

### Location
```
model/<model_name>/SQL/<folder_name>/folder.yml
```

### Example
```yaml
# SQL/001_Load__distr/folder.yml
001_Load__distr:
  enabled:
    contexts: [default]
  queries:
    001_RF110_Reg_Acc2:
      materialized: stage_calcid
  pre:
    - synch_iter
```

### Priority

Folder-level config overrides `model.yml` settings for the corresponding folder:
```
folder.yml > model.yml > template defaults
```

### Supported Configuration Keys

| Key | Description |
|-----|-------------|
| `enabled` | Enable/disable folder for specific contexts |
| `materialized` | Default materialization for folder |
| `queries.<query_name>.<key>` | Query-level settings |
| `pre` | Pre-macros for folder |
| `post` | Post-macros for folder |
| `cte` | CTE materialization config |
| `description` | Folder description |

### Loading

The framework loads `folder.yml` files automatically:
1. Load `model.yml` first
2. Scan `SQL/` directory for subfolders
3. Load `folder.yml` from each subfolder
4. Merge folder configs with model config (folder.yml takes precedence)

### Functions

```python
# FW/parsing/model_config_loader.py
load_folder_configs(model_path, sql_folder_name="SQL") -> Dict[str, FolderConfig]
merge_workflow_configs(base_config, folder_configs) -> WorkflowConfig
```

---

## Model Attribute Utilities

`FW/models/attribute_utils.py` - Central utilities:
```python
get_query_attribute_names(sql_model) -> Set[str]
get_key_attributes(target_table, sql_model) -> List[str]
get_update_attributes(target_table, key_attrs, sql_model) -> List[str]
get_required_attributes_not_in_query(target_table, sql_model) -> List[tuple]
format_attr_default_value(attr, domain_type) -> str
```

---

## Materialization: insert_fc

### Logic
```sql
INSERT INTO target_table (target_columns)
SELECT select_columns
FROM (
  <query>
) [t]
```

**target_columns**: key attrs + required attrs + attrs in query
**select_columns**: attrs from query + required attrs with default_value

### Errors
- "No key attributes found for insert_fc"
- "Required attribute 'X' is not present in query and has no default_value defined"

---

## Testing Workflow Changes

```bash
# Build workflow and save to JSON
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -o output.json
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -c vtb -o output.json

# Check output
python -c "import json; data = json.load(open('output.json')); print(json.dumps(data, indent=2))"
```

---

## Inline Configuration in SQL Files

You can define configuration directly inside SQL files using `@config()` blocks. The position of the block determines what it configures.

### Syntax
```sql
/*
@config(
  yml-compatible config
)
*/
```

### Configuration Types by Position

| Position | Configures |
|----------|------------|
| Start of file (before WITH/SELECT) | Query-level settings |
| Inside CTE (`cte_name as (/* @config */)`) | CTE-specific settings |
| Between SELECT and FROM | Next attribute in SELECT clause |

### Query-Level Configuration
```sql
/*
@config(
  enabled: true
  materialized: insert_fc
  attributes:
    - name: clientid
      domain_type: number
)
*/
with a as (select 1)
select clientid from a
```

### CTE-Level Configuration
```sql
with a as (
/*
@config(
  cte_materialization:
    default: ephemeral
    by_context:
      vtb: stage_calcid
  by_tool:
    postgresql: stage_calcid
  attributes:
    - name: col1
      domain_type: number
)
*/
select col1 from table1
```

### Attribute-Level Configuration
```sql
select
  id,
  /*
  @config(
    partition_key: 1,
    is_key: true,
    domain_type: number
  )
  */
  case when x = 1 then 2 end as type_code
from table1
```

### Priority Order
Inline config has the highest priority:
```
inline (SQL) > model.yml query > model.yml folder > model.yml workflow > defaults
```

### Parsing Module
**File:** `FW/parsing/inline_config_parser.py`
- `parse_inline_configs(sql_content)` - Parse all @config blocks
- `InlineConfigResult` - Result with `query_config`, `cte_configs`, `attr_configs`

### SQLMetadata Fields
```python
inline_query_config: Optional[Dict]     # Query-level config
inline_cte_configs: Dict[str, Dict]    # {cte_name: config}
inline_attr_configs: Dict[str, Dict]   # {attr_alias: config}
```

---

## Validation System

### Overview
The validation system checks projects against templates and runs customizable validation rules. It produces JSON and HTML reports with filtering and sorting capabilities.

### CLI Commands
```bash
# Validate specific model
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -c default

# Validate with specific rule categories
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -r "general,sql,adb,descriptions"

# Validate all models in project
python -m FW.cli validate "RF110NEW" -o validation_reports
```

### Validation Categories
Categories are defined in template's `validation_categories`:
- `general` - General checks (target_table, steps, tools)
- `sql` - SQL code checks (hints, DELETE, TRUNCATE, SELECT *)
- `adb` - ADB-specific checks (distribution_key, primary_key)
- `descriptions` - Description completeness checks

### Template Configuration
```yaml
# In templates (e.g., FW/config/templates/flx.yml)
models:
  - name: marts
    validation_categories:
      - general
      - sql
      - descriptions
      - adb
```

### Key Classes

**ValidationReport** (`FW/validation/models.py`)
```python
project_name: str
model_name: str
template_name: str
validation_categories: List[str]
timestamp: str
issues: List[ValidationIssue]
template_issues: List[ValidationIssue]

# Properties
total_issues: int
error_count: int
warning_count: int
info_count: int
```

**ValidationIssue** (`FW/validation/models.py`)
```python
level: ValidationLevel        # INFO, WARNING, ERROR
rule: str                     # Rule name
category: str                 # Category (general, sql, adb, descriptions)
message: str                  # Human-readable message
location: Optional[str]       # Where the issue was found
details: Dict[str, Any]      # Additional details
```

**BaseValidationRule** (`FW/validation/rules/base.py`)
```python
name: str                     # Rule identifier
category: str                 # Category
level: ValidationLevel        # Default level
description: str              # Human-readable description

def validate(self, workflow: "WorkflowModel") -> List[ValidationIssue]:
    """Execute validation rule - must be implemented by subclasses."""
    pass
```

**RuleRunner** (`FW/validation/rule_runner.py`)
```python
def __init__(self, categories: Optional[List[str]] = None)
def run(self, workflow: "WorkflowModel") -> List[ValidationIssue]
def get_available_categories(self) -> List[str]
```

**TemplateValidator** (`FW/validation/template_validator.py`)
```python
def validate(self, workflow: "WorkflowModel") -> List[ValidationIssue]
    # Validates: required folders, required queries
```

### Report Outputs
- **JSON**: `model_name_validation.json` - Machine-readable format for external systems
- **HTML**: `model_name_validation.html` - Interactive UI with filtering by level/category

### Creating Custom Rules
```python
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

class MyCustomRule(BaseValidationRule):
    name = "my_custom_rule"
    category = "general"  # or "sql", "adb", "descriptions"
    level = ValidationLevel.WARNING
    description = "Description of what this rule checks"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        # Check workflow and add issues
        return issues
```

### Files Structure
```
FW/validation/
├── __init__.py              # Exports
├── models.py                # ValidationReport, ValidationIssue, ValidationLevel
├── rule_runner.py           # RuleRunner, run_validation
├── template_validator.py    # TemplateValidator
├── html_generator.py       # generate_html_report, generate_json_report
└── rules/
    ├── __init__.py
    ├── base.py              # BaseValidationRule, ValidationRuleRegistry
    ├── sql/                 # SQL validation rules
    │   └── __init__.py     # NoHintsRule, NoDeleteStatementRule, etc.
    ├── adb/                 # ADB validation rules
    │   └── __init__.py     # DistributionKeyRule, AdbPrimaryKeyRule
    ├── descriptions/        # Description validation rules
    │   └── __init__.py     # MissingWorkflowDescriptionRule, etc.
    └── general/             # General validation rules
        └── __init__.py     # TargetTableRequiredRule, NoStepsRule, etc.
```
