"""Template loader - загрузка и валидация шаблонов."""
import yaml
from pathlib import Path
from typing import Optional

from FW.models import ProjectTemplate, ProjectConfig, ModelDefinition, ModelConfig, ModelRules
from FW.logging_config import get_logger


logger = get_logger("template_loader")


def get_template_dir() -> Path:
    """Получить путь к директории шаблонов."""
    fw_dir = Path(__file__).parent.parent
    return fw_dir / "config" / "templates"


def load_template(name: str) -> Optional[ProjectTemplate]:
    """Загрузить шаблон по имени.
    
    Args:
        name: имя шаблона
        
    Returns:
        ProjectTemplate или None если не найден
    """
    template_dir = get_template_dir()
    template_file = template_dir / f"{name}.yml"
    
    if not template_file.exists():
        logger.error(f"Template not found: {name} (file: {template_file})")
        return None
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        template = ProjectTemplate.from_dict(data)
        logger.info(f"Loaded template: {name}")
        return template
    
    except Exception as e:
        logger.error(f"Error loading template {name}: {e}")
        return None


def load_project_config(project_path: Path) -> Optional[ProjectConfig]:
    """Загрузить конфигурацию проекта из project.yml.
    
    Args:
        project_path: путь к проекту
        
    Returns:
        ProjectConfig или None если не найден
    """
    project_file = project_path / "project.yml"
    
    if not project_file.exists():
        logger.warning(f"project.yml not found in {project_path}")
        return None
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        return ProjectConfig.from_dict(data)
    
    except Exception as e:
        logger.error(f"Error loading project.yml: {e}")
        return None


def get_template_for_project(project_path: Path) -> Optional[ProjectTemplate]:
    """Получить шаблон для проекта.
    
    Args:
        project_path: путь к проекту
        
    Returns:
        ProjectTemplate или None
    """
    project_config = load_project_config(project_path)
    
    if not project_config:
        logger.error(f"Cannot load project config for {project_path}")
        return None
    
    if not project_config.template:
        logger.error(f"Project {project_config.name} has no template specified")
        return None
    
    template = load_template(project_config.template)
    
    if not template:
        return None
    
    return template


def merge_configs(
    template_config: ModelConfig,
    project_override: Optional[ModelConfig],
    model_config: ModelConfig
) -> ModelConfig:
    """Слить конфигурации с учетом приоритета.
    
    Приоритет (от низкого к высокому):
    template -> project -> model
    
    Args:
        template_config: конфигурация из шаблона
        project_override: переопределение из project.yml
        model_config: конфигурация модели
        
    Returns:
        Объединенная конфигурация
    """
    result = ModelConfig()
    
    result.builder = template_config.builder
    result.dependency_resolver = template_config.dependency_resolver
    result.workflow_engine = template_config.workflow_engine
    result.default_materialization = template_config.default_materialization
    result.model_ref_macro = template_config.model_ref_macro
    
    # Merge properties: template определяет, project переопределяет
    result.properties = {**template_config.properties}
    if project_override and project_override.properties:
        result.properties = {**result.properties, **project_override.properties}
    
    if project_override:
        if project_override.builder:
            result.builder = project_override.builder
        if project_override.dependency_resolver:
            result.dependency_resolver = project_override.dependency_resolver
        if project_override.workflow_engine:
            result.workflow_engine = project_override.workflow_engine
        if project_override.default_materialization:
            result.default_materialization = project_override.default_materialization
        if project_override.model_ref_macro:
            result.model_ref_macro = project_override.model_ref_macro
    
    if model_config.builder:
        result.builder = model_config.builder
    if model_config.dependency_resolver:
        result.dependency_resolver = model_config.dependency_resolver
    if model_config.workflow_engine:
        result.workflow_engine = model_config.workflow_engine
    if model_config.default_materialization:
        result.default_materialization = model_config.default_materialization
    if model_config.model_ref_macro:
        result.model_ref_macro = model_config.model_ref_macro
    
    return result


def merge_rules(
    template_rules: ModelRules,
    model_rules: ModelRules
) -> ModelRules:
    """Слить правила с учетом приоритета.
    
    Args:
        template_rules: правила из шаблона
        model_rules: правила модели
        
    Returns:
        Объединенные правила
    """
    result = ModelRules()
    
    result.folders = {**template_rules.folders, **model_rules.folders}
    result.queries = {**template_rules.queries, **model_rules.queries}
    result.parameters = {**template_rules.parameters, **model_rules.parameters}
    
    return result


def list_templates() -> list:
    """Список доступных шаблонов.
    
    Returns:
        Список имён шаблонов
    """
    template_dir = get_template_dir()
    
    if not template_dir.exists():
        return []
    
    templates = []
    for f in template_dir.glob("*.yml"):
        templates.append(f.stem)
    
    return sorted(templates)
