"""Context loader - loads contexts/*.yml."""

import yaml
from pathlib import Path
from typing import Dict, Optional, Any

from FW.models import ContextModel, ContextCollection
from FW.models.context import ContextConstants
from FW.logging_config import get_logger


logger = get_logger("context_loader")


def load_project_constants(project_path: Path) -> Dict[str, Dict[str, Any]]:
    """Загрузить константы из project.yml.

    Args:
        project_path: путь к директории проекта

    Returns:
        Словарь констант {name: {value, domain_type}}
    """
    project_file = project_path / "project.yml"
    if not project_file.exists():
        return {}

    try:
        with open(project_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        constants = data.get("constants", {})
        normalized = {}
        for key, value in constants.items():
            if isinstance(value, dict):
                normalized[key] = value
            else:
                normalized[key] = {"value": value, "domain_type": None}
        return normalized
    except Exception as e:
        logger.warning(f"Error loading project constants: {e}")
        return {}


def load_contexts(project_path: Path) -> ContextCollection:
    """Загрузить все контексты из директории contexts/.

    Args:
        project_path: путь к директории проекта

    Returns:
        ContextCollection со всеми контекстами
    """
    contexts_dir = project_path / "contexts"
    collection = ContextCollection()

    project_constants = load_project_constants(project_path)

    if not contexts_dir.exists():
        logger.warning(f"Contexts directory not found: {contexts_dir}")
        return collection

    for ctx_file in contexts_dir.glob("*.yml"):
        ctx_name = ctx_file.stem

        try:
            with open(ctx_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            constants_data = data.get("constants", {})
            context_constants = ContextConstants.from_dict(constants_data)

            merged_constants = dict(project_constants)
            for const_name, const_value in context_constants._constants.items():
                if const_name in merged_constants:
                    existing = merged_constants[const_name]
                    if isinstance(existing, dict) and isinstance(const_value, dict):
                        const_value_value = const_value.get("value")
                        if const_value_value is not None:
                            existing["value"] = const_value_value
                        const_value_domain = const_value.get("domain_type")
                        if const_value_domain is not None:
                            existing["domain_type"] = const_value_domain
                    else:
                        merged_constants[const_name] = const_value
                else:
                    merged_constants[const_name] = const_value

            data["constants"] = merged_constants

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
        with open(ctx_file, "r", encoding="utf-8") as f:
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
