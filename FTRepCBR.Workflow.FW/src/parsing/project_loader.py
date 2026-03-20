"""Project loader - loads project.yml."""
import yaml
from pathlib import Path
from typing import Optional

from FW.models import ProjectModel
from FW.logging_config import get_logger


logger = get_logger("project_loader")


def load_project(project_path: Path) -> Optional[ProjectModel]:
    """Загрузить модель проекта из project.yml.
    
    Args:
        project_path: путь к директории проекта
        
    Returns:
        ProjectModel или None если файл не найден
    """
    project_file = project_path / "project.yml"
    
    if not project_file.exists():
        logger.warning(f"project.yml not found in {project_path}")
        return None
    
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        if not data:
            logger.warning(f"Empty project.yml in {project_path}")
            return ProjectModel(name=project_path.name)
        
        return ProjectModel.from_dict(data)
    
    except Exception as e:
        logger.error(f"Error loading project.yml: {e}")
        return None


def get_project_name(project_path: Path) -> str:
    """Получить имя проекта.
    
    Args:
        project_path: путь к директории проекта
        
    Returns:
        Имя проекта или имя директории
    """
    project = load_project(project_path)
    if project:
        return project.name
    
    return project_path.name
