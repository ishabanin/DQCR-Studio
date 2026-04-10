"""Фабрика для создания resolver для workflow_new."""

from typing import Optional
from FW.models import ProjectTemplate, ModelDefinition
from FW.generation.dependency_resolvers.dependency_resolver import DependencyResolver
from FW.logging_config import get_logger

logger = get_logger("resolver_factory")

DEFAULT_RESOLVER = "naming_convention"


def get_resolver_name_for_workflow_new(
    template: Optional[ProjectTemplate],
    model_definition: Optional[ModelDefinition],
) -> str:
    """Определить имя resolver на основе шаблона и модели.
    
    Priority:
    1. template.model.config.dependency_resolver
    2. model_definition.config.dependency_resolver
    3. DEFAULT_RESOLVER
    
    Args:
        template: шаблон проекта
        model_definition: определение модели
    
    Returns:
        Имя resolver (naming_convention, graph_based, explicit)
    """
    resolver_name = DEFAULT_RESOLVER
    
    if template and model_definition:
        template_model = template.get_model(model_definition.name)
        if template_model and template_model.config and template_model.config.dependency_resolver:
            resolver_name = template_model.config.dependency_resolver
        elif model_definition.config and model_definition.config.dependency_resolver:
            resolver_name = model_definition.config.dependency_resolver
    
    return resolver_name


def create_resolver_for_workflow_new(
    template: Optional[ProjectTemplate],
    model_definition: Optional[ModelDefinition],
) -> DependencyResolver:
    """Создать экземпляр resolver для workflow_new.
    
    Args:
        template: шаблон проекта
        model_definition: определение модели
    
    Returns:
        Экземпляр DependencyResolver
    """
    from FW.generation.dependency_resolvers.naming_convention_new import NamingConventionResolverNew
    
    resolver_name = get_resolver_name_for_workflow_new(template, model_definition)
    
    if resolver_name == "naming_convention":
        return NamingConventionResolverNew()
    
    raise ValueError(f"Resolver '{resolver_name}' not supported for workflow_new. Only 'naming_convention' is available.")