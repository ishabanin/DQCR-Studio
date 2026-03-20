"""Builder registry - динамическая загрузка builders."""
import importlib
from typing import Type, Dict, Optional, Any

from FW.generation.base import BaseWorkflowBuilder
from FW.generation.resolver_registry import create_resolver
from FW.generation.dependency_resolver import DependencyResolver
from FW.logging_config import get_logger


logger = get_logger("builder_registry")

BUILDER_REGISTRY: Dict[str, str] = {
    "default": "DefaultBuilder",
    "graph": "GraphBuilder",
    "naming": "NamingConventionBuilder",
}


def get_builder_class(name: str) -> Type[BaseWorkflowBuilder]:
    """Получить класс builder по имени.
    
    Args:
        name: имя builder (default, graph, naming)
        
    Returns:
        Класс builder
        
    Raises:
        ValueError: если builder не найден
    """
    class_name = BUILDER_REGISTRY.get(name)
    if not class_name:
        logger.warning(f"Builder '{name}' not found, using 'default'")
        class_name = "DefaultBuilder"
    
    module_name = class_name.lower()
    try:
        module = importlib.import_module(f"FW.generation.{module_name}")
        builder_class = getattr(module, class_name)
        return builder_class
    except (ImportError, AttributeError) as e:
        logger.error(f"Error loading builder {name}: {e}")
        raise ValueError(f"Builder '{name}' not found") from e


def get_builder(
    name: str,
    project_path,
    tool_registry,
    macro_registry,
    function_registry=None,
    dependency_resolver=None,
    workflow_engine: Optional[str] = None,
    **kwargs
) -> BaseWorkflowBuilder:
    """Создать экземпляр builder по имени.
    
    Args:
        name: имя builder
        project_path: путь к проекту
        tool_registry: реестр tools
        macro_registry: реестр макросов
        function_registry: реестр функций
        dependency_resolver: резолвер зависимостей
        workflow_engine: workflow engine
        **kwargs: дополнительные параметры
        
    Returns:
        Экземпляр builder
    """
    builder_class = get_builder_class(name)
    return builder_class(
        project_path=project_path,
        tool_registry=tool_registry,
        macro_registry=macro_registry,
        function_registry=function_registry,
        dependency_resolver=dependency_resolver,
        workflow_engine=workflow_engine,
        **kwargs
    )


def list_builders() -> list:
    """Список доступных builders.
    
    Returns:
        Список имён builders
    """
    return list(BUILDER_REGISTRY.keys())


def get_or_create_resolver(resolver_name: str = None) -> Optional[DependencyResolver]:
    """Получить или создать resolver по имени из конфига.
    
    Args:
        resolver_name: имя resolver из конфига (naming_convention, graph_based, explicit)
    
    Returns:
        Экземпляр resolver или None
    """
    if resolver_name:
        return create_resolver(resolver_name)
    return None
