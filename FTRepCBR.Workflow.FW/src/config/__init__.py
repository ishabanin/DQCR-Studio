"""Tool and workflow engine registry."""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from FW.logging_config import get_logger
from FW.models.workflow_engine import WorkflowEngineModel
from FW.exceptions import ConfigValidationError


logger = get_logger("config")


@dataclass
class ToolConfig:
    """Конфигурация tool."""
    name: str
    default_materialization: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    domain2basetype: Dict = None


class ToolRegistry:
    """Реестр доступных tools."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self._tools: Dict[str, ToolConfig] = {}
        self._default_materialization: Optional[str] = None
        self._config_path = config_path or self._get_default_config_path()
        self._load()
    
    def _get_default_config_path(self) -> Path:
        """Получить путь к конфигу по умолчанию."""
        fw_dir = Path(__file__).parent.parent
        return fw_dir / "config" / "tools.yml"
    
    def _load(self):
        """Загрузить конфигурацию tools."""
        if not self._config_path.exists():
            raise ConfigValidationError(f"Tools config not found: {self._config_path}")
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            tools_list = config.get('tools', [])
            for tool in tools_list:
                for tool_name in tool:
                   self._tools[tool_name] = ToolConfig(
                       name=tool_name,
                       default_materialization=config.get('default_materialization'),
                       domain2basetype=tool[tool_name].get("domain2basetype")
                   )        
            self._default_materialization = config.get('default_materialization')
            
            logger.info(f"Loaded {len(self._tools)} tools: {list(self._tools.keys())}")
            
        except ConfigValidationError:
            raise
        except Exception as e:
            logger.error(f"Error loading tools config: {e}")
            raise ConfigValidationError(f"Failed to load tools config: {e}")
    
    @property
    def tools(self) -> List[str]:
        """Список доступных tools."""
        return list(self._tools.keys())

    @property
    def toolsConfig(self) -> List[str]:
        """Список доступных tools."""
        return self._tools
        
    @property
    def default_materialization(self) -> Optional[str]:
        """Materialization по умолчанию."""
        if self._default_materialization is None:
            raise ConfigValidationError(
                "default_materialization must be specified in tools.yml",
                field="default_materialization"
            )
        return self._default_materialization
    
    def get(self, name: str) -> Optional[ToolConfig]:
        """Получить конфигурацию tool по имени."""
        return self._tools.get(name)
    
    def has_tool(self, name: str) -> bool:
        """Проверить существование tool."""
        return name in self._tools
    
    def get_tools_for_project(self, project_tools: Optional[Set[str]] = None) -> List[str]:
        """Получить tools для проекта."""
        if project_tools:
            return [t for t in self.tools if t in project_tools]
        return self.tools


_default_registry: Optional[ToolRegistry] = None
_default_workflow_engine_registry: Optional["WorkflowEngineRegistry"] = None


def get_tool_registry(config_path: Optional[Path] = None) -> ToolRegistry:
    """Получить глобальный экземпляр ToolRegistry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry(config_path)
    return _default_registry


class WorkflowEngineRegistry:
    """Реестр workflow engines."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self._engines: Dict[str, WorkflowEngineModel] = {}
        self._default: Optional[str] = None
        self._config_path = config_path or self._get_default_config_path()
        self._load()
    
    def _get_default_config_path(self) -> Path:
        """Получить путь к конфигу по умолчанию."""
        fw_dir = Path(__file__).parent.parent
        return fw_dir / "config" / "workflow_engines.yml"
    
    def _load(self):
        """Загрузить конфигурацию workflow engines."""
        if not self._config_path.exists():
            raise ConfigValidationError(
                f"Workflow engines config not found: {self._config_path}"
            )
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            engines_data = config.get('engines', {})
            for engine_name, engine_data in engines_data.items():
                self._engines[engine_name] = WorkflowEngineModel.from_dict(
                    engine_name, engine_data
                )
            
            self._default = config.get('default')
            
            logger.info(f"Loaded {len(self._engines)} workflow engines: {list(self._engines.keys())}")
            
        except ConfigValidationError:
            raise
        except Exception as e:
            logger.error(f"Error loading workflow engines config: {e}")
            raise ConfigValidationError(f"Failed to load workflow engines config: {e}")
    
    @property
    def engines(self) -> List[str]:
        """Список доступных engines."""
        return list(self._engines.keys())
    
    @property
    def default(self) -> Optional[str]:
        """Engine по умолчанию."""
        return self._default
    
    def get(self, name: str) -> Optional[WorkflowEngineModel]:
        """Получить engine по имени."""
        return self._engines.get(name)
    
    def has_engine(self, name: str) -> bool:
        """Проверить существование engine."""
        return name in self._engines


def get_workflow_engine_registry(config_path: Optional[Path] = None) -> WorkflowEngineRegistry:
    """Получить глобальный экземпляр WorkflowEngineRegistry."""
    global _default_workflow_engine_registry
    if _default_workflow_engine_registry is None:
        _default_workflow_engine_registry = WorkflowEngineRegistry(config_path)
    return _default_workflow_engine_registry


_default_template_registry: Optional["TemplateRegistry"] = None


class TemplateRegistry:
    """Реестр шаблонов проектов."""
    
    def __init__(self):
        self._templates: Dict[str, "ProjectTemplate"] = {}
        self._load()
    
    def _load(self):
        """Загрузить все шаблоны из директории."""
        from FW.parsing.template_loader import list_templates, load_template
        from FW.models import ProjectTemplate
        
        template_names = list_templates()
        
        for name in template_names:
            template = load_template(name)
            if template:
                self._templates[name] = template
        
        logger.info(f"Loaded {len(self._templates)} templates: {list(self._templates.keys())}")
    
    @property
    def templates(self) -> List[str]:
        """Список доступных шаблонов."""
        return list(self._templates.keys())
    
    def get(self, name: str) -> Optional["ProjectTemplate"]:
        """Получить шаблон по имени."""
        return self._templates.get(name)
    
    def has_template(self, name: str) -> bool:
        """Проверить существование шаблона."""
        return name in self._templates


def get_template_registry() -> TemplateRegistry:
    """Получить глобальный экземпляр TemplateRegistry."""
    global _default_template_registry
    if _default_template_registry is None:
        _default_template_registry = TemplateRegistry()
    return _default_template_registry
