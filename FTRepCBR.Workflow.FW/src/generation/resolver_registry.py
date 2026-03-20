"""Generation - resolver registry."""
from typing import Type, Optional
import importlib

from FW.generation.dependency_resolver import DependencyResolver
from FW.logging_config import get_logger


logger = get_logger("resolver_registry")

RESOLVER_REGISTRY = {
    "naming_convention": "NamingConventionResolver",
    "graph_based": "GraphBasedResolver",
    "explicit": "ExplicitDependencyResolver",
}


def get_resolver_class(name: str) -> Type[DependencyResolver]:
    """Получить класс resolver по имени.

    Args:
        name: имя resolver (naming_convention, graph_based, explicit)

    Returns:
        Класс resolver

    Raises:
        ValueError: если resolver не найден
    """
    class_name = RESOLVER_REGISTRY.get(name)
    if not class_name:
        logger.warning(f"Resolver '{name}' not found, using 'naming_convention'")
        class_name = "NamingConventionResolver"

    module_map = {
        "NamingConventionResolver": "naming_convention",
        "GraphBasedResolver": "graph_based",
        "ExplicitDependencyResolver": "explicit",
    }

    module_name = module_map.get(class_name, class_name.lower())
    try:
        module = importlib.import_module(f"FW.generation.{module_name}")
        resolver_class = getattr(module, class_name)
        return resolver_class
    except (ImportError, AttributeError) as e:
        logger.error(f"Error loading resolver {name}: {e}")
        raise ValueError(f"Resolver '{name}' not found") from e


def create_resolver(name: str = "naming_convention") -> DependencyResolver:
    """Создать экземпляр resolver по имени.

    Args:
        name: имя resolver

    Returns:
        Экземпляр resolver
    """
    resolver_class = get_resolver_class(name)
    return resolver_class()


def list_resolvers() -> list:
    """Список доступных resolvers.

    Returns:
        Список имён resolvers
    """
    return list(RESOLVER_REGISTRY.keys())
