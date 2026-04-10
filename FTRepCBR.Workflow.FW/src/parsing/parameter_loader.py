"""Parameter loader - loads parameters from project and model directories."""
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from FW.models import ParameterModel
from FW.logging_config import get_logger


logger = get_logger("parameter_loader")


def load_global_parameters(project_path: Path, global_params) -> Dict[str, ParameterModel]:
    """Загрузить глобальные параметры из parameters/.
    
    Args:
        project_path: путь к директории проекта
        
    Returns:
        Словарь {name: ParameterModel}
    """
    params_dir = project_path / global_params
    result = {}
    
    if not params_dir.exists():
        logger.warning(f"Global parameters directory not found: {params_dir}")
        return result
    
    for param_file in params_dir.glob("*.yml"):
        param_name = param_file.stem
        
        try:
            with open(param_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            param_model = ParameterModel.from_dict(param_name, data)
            result[param_name] = param_model
            logger.info(f"Loaded global parameter: {param_name}")
            
        except Exception as e:
            logger.error(f"Error loading parameter {param_file}: {e}")
    
    return result


def load_model_parameters(model_path, local_params) -> Dict[str, ParameterModel]:
    """Загрузить локальные параметры модели из model/{name}/parameters/.
    
    Args:
        project_path: путь к директории проекта
        model_name: имя модели
        
    Returns:
        Словарь {name: ParameterModel}
    """
    params_dir = model_path / local_params
    result = {}
    
    if not params_dir.exists():
        logger.warning(f"Model parameters directory not found: {params_dir}")
        return result
    
    for param_file in params_dir.glob("*.yml"):
        param_name = param_file.stem
        
        try:
            with open(param_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            param_model = ParameterModel.from_dict(param_name, data)
            result[param_name] = param_model
            logger.info(f"Loaded model parameter: {model_name}.{param_name}")
            
        except Exception as e:
            logger.error(f"Error loading parameter {param_file}: {e}")
    
    return result


def load_parameters(project_path, model_path, local_params, global_params) -> Dict[str, ParameterModel]:
    """Загрузить параметры с учетом приоритета (локальные переопределяют глобальные).
    
    Args:
        project_path: путь к директории проекта
        model_name: имя модели (опционально)
        
    Returns:
        Словарь {name: ParameterModel} с учетом приоритета
    """
    result = {}
    
    global_params = load_global_parameters(project_path, global_params)
    result.update(global_params)
    
    if model_path:
        model_params = load_model_parameters(model_path, local_params)
        result.update(model_params)
        logger.info(f"Merged {len(global_params)} global + {len(model_params)} model parameters")
    else:
        logger.info(f"Loaded {len(global_params)} global parameters")
    
    return result
