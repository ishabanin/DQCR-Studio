"""Model config loader - loads model.yml for each model."""
import yaml
from pathlib import Path
from typing import Optional, Dict

from FW.models import WorkflowConfig, TargetTableModel, FolderConfig
from FW.models.attribute import Attribute
from FW.models.workflow import CTEMaterializationConfig
from FW.logging_config import get_logger


logger = get_logger("model_config_loader")


def load_model_config(model_path: Path) -> WorkflowConfig:
    """Загрузить конфигурацию модели из model.yml.
    
    Args:
        model_path: путь к директории модели (model/{name}/)
        
    Returns:
        WorkflowConfig
    """
    model_yml = model_path / "model.yml"
    
    if not model_yml.exists():
        logger.warning(f"model.yml not found in {model_path}")
        return WorkflowConfig()
    
    try:
        with open(model_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        workflow_data = data.get("workflow", {})
        config = WorkflowConfig.from_dict(workflow_data)
        
        logger.info(f"Loaded model config from {model_yml}")
        return config
    
    except Exception as e:
        logger.error(f"Error loading model.yml: {e}")
        return WorkflowConfig()


def load_target_table(model_path: Path, default_name: str = "") -> TargetTableModel:
    """Загрузить конфигурацию целевой таблицы.
    
    Args:
        model_path: путь к директории модели
        default_name: имя по умолчанию (если не указано в model.yml)
        
    Returns:
        TargetTableModel
    """
    model_yml = model_path / "model.yml"
    
    if not model_yml.exists():
        return TargetTableModel(name=default_name)
    
    try:
        with open(model_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        target_data = data.get("target_table", {})
        
        table_name = target_data.get("name", default_name)
        schema = target_data.get("schema")
        description = target_data.get("description", "")
        
        attrs_data = target_data.get("attributes", [])
        attributes = [Attribute.from_dict(a) for a in attrs_data]
        
        cte_data = data.get("cte")
        cte = CTEMaterializationConfig.from_dict(cte_data)
        
        return TargetTableModel(
            name=table_name,
            schema=schema,
            description=description,
            attributes=attributes,
        )
    
    except Exception as e:
        logger.error(f"Error loading target table from model.yml: {e}")
        return TargetTableModel(name=default_name)


def get_model_names(project_path: Path) -> list:
    """Получить список моделей в проекте.
    
    Args:
        project_path: путь к директории проекта
        
    Returns:
        Список имен моделей
    """
    model_dir = project_path / "model"
    
    if not model_dir.exists():
        return []
    
    return [f.name for f in model_dir.iterdir() if f.is_dir()]


def load_folder_configs(model_path: Path, sql_folder_name: str = "SQL") -> Dict[str, FolderConfig]:
    """Загрузить конфигурации папок из folder.yml файлов.
    
    Сканирует директорию SQL/ в модели и загружает folder.yml из каждой подпапки.
    
    Args:
        model_path: путь к директории модели (model/{name}/)
        sql_folder_name: имя папки с SQL файлами (по умолчанию "SQL")
        
    Returns:
        Словарь {folder_name: FolderConfig}
    """
    sql_dir = model_path / sql_folder_name
    
    if not sql_dir.exists():
        logger.warning(f"SQL directory not found: {sql_dir}")
        return {}
    
    folder_configs = {}
    
    for folder_path in sql_dir.iterdir():
        if not folder_path.is_dir():
            continue
        
        folder_yml = folder_path / "folder.yml"
        
        if not folder_yml.exists():
            continue
        
        try:
            with open(folder_yml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            if not data:
                continue
            
            for folder_name, folder_data in data.items():
                if not isinstance(folder_data, dict):
                    logger.warning(f"Invalid folder config in {folder_yml}: expected dict, got {type(folder_data)}")
                    continue
                
                folder_configs[folder_name] = FolderConfig.from_dict(folder_data)
                logger.info(f"Loaded folder config from {folder_yml} for folder '{folder_name}'")
        
        except Exception as e:
            logger.error(f"Error loading folder.yml from {folder_yml}: {e}")
            continue
    
    return folder_configs


def merge_workflow_configs(base_config: WorkflowConfig, folder_configs: Dict[str, FolderConfig]) -> WorkflowConfig:
    """Слить базовый конфиг с конфигами из folder.yml.
    
    Конфиги из folder_configs переопределяют значения из base_config.
    Переопределяются только явно указанные поля.
    
    Args:
        base_config: базовый конфиг из model.yml
        folder_configs: словарь конфигов из folder.yml
        
    Returns:
        WorkflowConfig с объединёнными настройками
    """
    if not base_config:
        base_config = WorkflowConfig()
    
    if not folder_configs:
        return base_config
    
    for folder_name, folder_config in folder_configs.items():
        if folder_name not in base_config.folders:
            base_config.folders[folder_name] = FolderConfig()
        
        base_folder = base_config.folders[folder_name]
        
        if folder_config.enabled is not None:
            base_folder.enabled = folder_config.enabled
        
        if folder_config.materialized is not None:
            base_folder.materialized = folder_config.materialized
        
        if folder_config.description:
            base_folder.description = folder_config.description
        
        if folder_config.pre:
            base_folder.pre = folder_config.pre
        
        if folder_config.post:
            base_folder.post = folder_config.post
        
        if folder_config.cte is not None:
            base_folder.cte = folder_config.cte
        
        if folder_config.queries:
            for query_name, query_config in folder_config.queries.items():
                if query_name not in base_folder.queries:
                    base_folder.queries[query_name] = query_config
                else:
                    base_query = base_folder.queries[query_name]
                    
                    if query_config.enabled is not None:
                        base_query.enabled = query_config.enabled
                    
                    if query_config.materialized is not None:
                        base_query.materialized = query_config.materialized
                    
                    if query_config.description:
                        base_query.description = query_config.description
                    
                    if query_config.attributes:
                        base_query.attributes = query_config.attributes
                    
                    if query_config.cte is not None:
                        base_query.cte = query_config.cte
        
        logger.debug(f"Merged folder config for '{folder_name}'")
    
    return base_config
