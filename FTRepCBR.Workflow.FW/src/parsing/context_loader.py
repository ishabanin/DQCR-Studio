"""Context loader - loads contexts/*.yml."""
import yaml
from pathlib import Path
from typing import Dict, Optional

from FW.models import ContextModel, ContextCollection
from FW.logging_config import get_logger


logger = get_logger("context_loader")


def load_contexts(project_path: Path) -> ContextCollection:
    """Загрузить все контексты из директории contexts/.
    
    Args:
        project_path: путь к директории проекта
        
    Returns:
        ContextCollection со всеми контекстами
    """
    contexts_dir = project_path / "contexts"
    collection = ContextCollection()
    
    if not contexts_dir.exists():
        logger.warning(f"Contexts directory not found: {contexts_dir}")
        return collection
    
    for ctx_file in contexts_dir.glob("*.yml"):
        ctx_name = ctx_file.stem
        
        try:
            with open(ctx_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            context = ContextModel.from_dict(ctx_name, data)
            collection.add(context)
            logger.info(f"Loaded context: {ctx_name}")
            
        except Exception as e:
            logger.error(f"Error loading context {ctx_file}: {e}")
    
    if not collection.list_names():
        logger.warning(f"No contexts loaded from {contexts_dir}")
    
    return collection


def load_context(project_path: Path, context_name: str) -> Optional[ContextModel]:
    """Загрузить конкретный контекст.
    
    Args:
        project_path: путь к директории проекта
        context_name: имя контекста
        
    Returns:
        ContextModel или None если не найден
    """
    ctx_file = project_path / "contexts" / f"{context_name}.yml"
    
    if not ctx_file.exists():
        logger.warning(f"Context file not found: {ctx_file}")
        return None
    
    try:
        with open(ctx_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        return ContextModel.from_dict(context_name, data)
    
    except Exception as e:
        logger.error(f"Error loading context {ctx_file}: {e}")
        return None


def get_context_names(project_path: Path) -> list:
    """Получить список имен контекстов в проекте.
    
    Args:
        project_path: путь к директории проекта
        
    Returns:
        Список имен контекстов
    """
    contexts_dir = project_path / "contexts"
    
    if not contexts_dir.exists():
        return []
    
    return [f.stem for f in contexts_dir.glob("*.yml")]
