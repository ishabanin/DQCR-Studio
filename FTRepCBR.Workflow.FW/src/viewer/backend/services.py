"""FW viewer backend services - CLI integration layer."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _run_cli_command(args: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Run FW CLI command via subprocess."""
    project_root = Path(__file__).parent.parent.parent.parent
    
    cmd = ["python", "-m", "FW.cli"] + args
    
    env = {"PYTHONPATH": str(project_root)}
    env.update(os.environ)
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or project_root,
        env=env
    )
    
    if result.returncode != 0:
        error_msg = result.stderr or "Unknown error"
        raise ViewerServiceError(f"CLI command failed: {error_msg}")
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ViewerServiceError(f"Failed to parse CLI output: {e}\nOutput: {result.stdout}")


def _read_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Read and parse YAML file."""
    if not file_path.exists():
        raise ViewerServiceError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _get_relative_path(base: Path, full: Path) -> str:
    """Get relative path from base to full path."""
    return str(full.relative_to(base))


def list_models_in_project(project_path: Path) -> List[str]:
    """Get list of model names in project."""
    model_dir = project_path / "model"
    if not model_dir.exists():
        return []
    
    models = []
    for item in model_dir.iterdir():
        if item.is_dir() and (item / "model.yml").exists():
            models.append(item.name)
    
    return sorted(models)


def list_contexts_in_project(project_path: Path) -> List[str]:
    """Get list of context names in project."""
    contexts_dir = project_path / "contexts"
    if not contexts_dir.exists():
        return []
    
    contexts = []
    for item in contexts_dir.iterdir():
        if item.suffix in ['.yml', '.yaml']:
            contexts.append(item.stem)
    
    return sorted(contexts)


def build_workflow(
    project_path: str,
    model_name: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Build workflow model via CLI and return JSON."""
    project_root = Path(__file__).parent.parent.parent.parent
    
    args = ["build", project_path, model_name]
    if context:
        args.extend(["-c", context])
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        args.extend(["-o", tmp_path])
        
        env = {"PYTHONPATH": str(project_root)}
        env.update(os.environ)
        
        result = subprocess.run(
            ["python", "-m", "FW.cli"] + args,
            capture_output=True,
            text=True,
            cwd=project_root,
            env=env
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout[:500]
            raise ViewerServiceError(f"CLI command failed: {error_msg}")
        
        with open(tmp_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        all_contexts = list_contexts_in_project(Path(project_path))
        if 'all' not in all_contexts:
            all_contexts.insert(0, 'all')
        workflow_data['project_contexts'] = all_contexts
        return workflow_data
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def load_project_config(project_path: Path) -> Dict[str, Any]:
    """Load project.yml."""
    config_path = project_path / "project.yml"
    return _read_yaml_file(config_path)


def load_config(project_path: Path, config_type: str, relative_path: str) -> Dict[str, Any]:
    """Load config file by type and relative path."""
    normalized_path = relative_path.replace('\\', '/')
    full_path = project_path / normalized_path
    
    if config_type == 'sql':
        raise ViewerServiceError("Use /api/sql endpoint for SQL files")
    if config_type == 'graph':
        raise ViewerServiceError("Graph is not a config file")
    
    return _read_yaml_file(full_path)


def load_model_config(project_path: Path, model_name: str) -> Dict[str, Any]:
    """Load model.yml for specific model."""
    config_path = project_path / "model" / model_name / "model.yml"
    return _read_yaml_file(config_path)


def load_folder_config(project_path: Path, model_name: str, folder_name: str) -> Dict[str, Any]:
    """Load folder.yml for specific folder."""
    sql_dir = project_path / "model" / model_name / "SQL"
    
    for folder_path in sql_dir.iterdir():
        if folder_path.is_dir() and folder_path.name == folder_name:
            config_path = folder_path / "folder.yml"
            if config_path.exists():
                return _read_yaml_file(config_path)
    
    return {}


def load_context_config(project_path: Path, context_name: str) -> Dict[str, Any]:
    """Load context.yml for specific context."""
    config_path = project_path / "contexts" / f"{context_name}.yml"
    return _read_yaml_file(config_path)


def load_model_parameters(project_path: Path, model_name: str) -> List[Dict[str, Any]]:
    """Load all parameter files in model's parameters folder."""
    params_dir = project_path / "model" / model_name / "parameters"
    if not params_dir.exists():
        return []
    
    params = []
    for param_file in params_dir.iterdir():
        if param_file.suffix in ['.yml', '.yaml']:
            param_data = _read_yaml_file(param_file)
            param_data['_file'] = str(param_file.relative_to(project_path))
            params.append(param_data)
    
    return sorted(params, key=lambda x: x.get('_file', ''))


def get_project_tree(project_path: Path, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Build project tree structure."""
    rel = lambda p: _get_relative_path(project_path, p)
    
    tree = {
        'name': project_path.name,
        'path': rel(project_path),
        'type': 'project',
        'children': []
    }
    
    children = tree['children']
    
    if (project_path / "project.yml").exists():
        children.append({
            'name': 'project.yml',
            'path': rel(project_path / "project.yml"),
            'type': 'config',
            'configType': 'project'
        })
    
    contexts_dir = project_path / "contexts"
    if contexts_dir.exists():
        contexts_node = {
            'name': 'contexts',
            'path': rel(contexts_dir),
            'type': 'folder',
            'children': []
        }
        for ctx_file in sorted(contexts_dir.iterdir()):
            if ctx_file.suffix in ['.yml', '.yaml']:
                contexts_node['children'].append({
                    'name': ctx_file.name,
                    'path': rel(ctx_file),
                    'type': 'config',
                    'configType': 'context'
                })
        if contexts_node['children']:
            children.append(contexts_node)
    
    if model_name:
        model_dir = project_path / "model" / model_name
        if model_dir.exists():
            model_node = {
                'name': model_name,
                'path': rel(model_dir),
                'type': 'folder',
                'configType': 'model',
                'children': []
            }
            
            model_config_path = model_dir / "model.yml"
            if model_config_path.exists():
                model_node['children'].append({
                    'name': 'model.yml',
                    'path': rel(model_config_path),
                    'type': 'config',
                    'configType': 'model'
                })
            
            sql_dir = model_dir / "SQL"
            if sql_dir.exists():
                sql_node = {
                    'name': 'SQL',
                    'path': rel(sql_dir),
                    'type': 'folder',
                    'children': []
                }
                
                for folder_path in sorted(sql_dir.iterdir()):
                    if folder_path.is_dir():
                        folder_node = {
                            'name': folder_path.name,
                            'path': rel(folder_path),
                            'type': 'folder',
                            'children': []
                        }
                        
                        folder_config_path = folder_path / "folder.yml"
                        if folder_config_path.exists():
                            folder_node['children'].append({
                                'name': 'folder.yml',
                                'path': rel(folder_config_path),
                                'type': 'config',
                                'configType': 'folder'
                            })
                        
                        for sql_file in sorted(folder_path.iterdir()):
                            if sql_file.suffix == '.sql':
                                folder_node['children'].append({
                                    'name': sql_file.name,
                                    'path': rel(sql_file),
                                    'type': 'sql'
                                })
                        
                        sql_node['children'].append(folder_node)
                
                model_node['children'].append(sql_node)
            
            params_dir = model_dir / "parameters"
            if params_dir.exists():
                params_node = {
                    'name': 'parameters',
                    'path': rel(params_dir),
                    'type': 'folder',
                    'children': []
                }
                
                for param_file in sorted(params_dir.iterdir()):
                    if param_file.suffix in ['.yml', '.yaml']:
                        params_node['children'].append({
                            'name': param_file.name,
                            'path': rel(param_file),
                            'type': 'config',
                            'configType': 'parameter'
                        })
                
                if params_node['children']:
                    model_node['children'].append(params_node)
            
            model_node['children'].append({
                'name': 'Graph',
                'path': '__graph__',
                'type': 'graph'
            })
            
            children.append(model_node)
    
    return tree


def get_available_materializations() -> List[str]:
    """Get list of available materialization types."""
    return [
        "insert_fc",
        "upsert_fc", 
        "stage_calcid",
        "ephemeral",
        "param"
    ]


def validate_workflow(
    project_path: str,
    model_name: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Validate workflow model via CLI and return validation report JSON."""
    project_root = Path(__file__).parent.parent.parent.parent
    
    args = ["validate", project_path, model_name]
    if context:
        args.extend(["-c", context])
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        args.extend(["-o", str(tmp_path)])
        
        env = {"PYTHONPATH": str(project_root)}
        env.update(os.environ)
        
        result = subprocess.run(
            ["python", "-m", "FW.cli"] + args,
            capture_output=True,
            text=True,
            cwd=project_root,
            env=env
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout[:500]
            raise ViewerServiceError(f"CLI validate command failed: {error_msg}")
        
        json_file = tmp_path / f"{model_name}_validation.json"
        with open(json_file, 'r', encoding='utf-8') as f:
            validation_data = json.load(f)
        
        return validation_data


class ViewerServiceError(Exception):
    """Error in viewer service."""
    pass
