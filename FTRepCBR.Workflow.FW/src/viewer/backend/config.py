"""Configuration for FW viewer."""
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
import yaml


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


class GraphConfig(BaseModel):
    default_filter_context: Optional[str] = None
    show_ephemeral: bool = True
    show_disabled: bool = False


class EditorConfig(BaseModel):
    sql_highlighting: str = "prism"
    max_sql_lines: int = 1000


class ViewerConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    graph: GraphConfig = GraphConfig()
    editor: EditorConfig = EditorConfig()
    recent_paths: List[str] = []
    max_recent: int = 10


def load_config(config_path: Optional[Path] = None) -> ViewerConfig:
    """Load viewer configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yml"
    
    if not config_path.exists():
        return ViewerConfig()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    
    return ViewerConfig(**data)


def save_config(config: ViewerConfig, config_path: Optional[Path] = None) -> None:
    """Save viewer configuration to YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yml"
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)


CONFIG = load_config()
