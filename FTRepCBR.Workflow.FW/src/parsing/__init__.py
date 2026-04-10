"""Parsing package."""
from FW.parsing.sql_metadata import SQLMetadata, SQLMetadataParser


__all__ = ['SQLMetadata', 'SQLMetadataParser']


def load_project(project_path):
    """Загрузить проект."""
    from FW.parsing.project_loader import load_project as _load
    return _load(project_path)


def get_project_name(project_path):
    """Получить имя проекта."""
    from FW.parsing.project_loader import get_project_name as _get
    return _get(project_path)


def load_contexts(project_path):
    """Загрузить контексты."""
    from FW.parsing.context_loader import load_contexts as _load
    return _load(project_path)


def load_context(project_path, context_name):
    """Загрузить контекст."""
    from FW.parsing.context_loader import load_context as _load
    return _load(project_path, context_name)


def get_context_names(project_path):
    """Получить имена контекстов."""
    from FW.parsing.context_loader import get_context_names as _get
    return _get(project_path)


def load_parameters(project_path, model_path, local_params, global_params):
    """Загрузить параметры."""
    from FW.parsing.parameter_loader import load_parameters as _load
    return _load(project_path, model_path, local_params, global_params)


def load_global_parameters(project_path):
    """Загрузить глобальные параметры."""
    from FW.parsing.parameter_loader import load_global_parameters as _load
    return _load(project_path)


def load_model_parameters(project_path, model_name):
    """Загрузить параметры модели."""
    from FW.parsing.parameter_loader import load_model_parameters as _load
    return _load(project_path, model_name)


def load_model_config(model_path):
    """Загрузить конфиг модели."""
    from FW.parsing.model_config_loader import load_model_config as _load
    return _load(model_path)


def load_target_table(model_path, default_name=""):
    """Загрузить целевую таблицу."""
    from FW.parsing.model_config_loader import load_target_table as _load
    return _load(model_path, default_name)


def get_model_names(project_path):
    """Получить имена моделей."""
    from FW.parsing.model_config_loader import get_model_names as _get
    return _get(project_path)


def load_folder_configs(model_path, sql_folder_name="SQL"):
    """Загрузить конфигурации папок из folder.yml."""
    from FW.parsing.model_config_loader import load_folder_configs as _load
    return _load(model_path, sql_folder_name)


def merge_workflow_configs(base_config, folder_configs):
    """Слить базовый конфиг с конфигами из folder.yml."""
    from FW.parsing.model_config_loader import merge_workflow_configs as _merge
    return _merge(base_config, folder_configs)


def load_template(name):
    """Загрузить шаблон по имени."""
    from FW.parsing.template_loader import load_template as _load
    return _load(name)


def load_project_config(project_path):
    """Загрузить конфигурацию проекта."""
    from FW.parsing.template_loader import load_project_config as _load
    return _load(project_path)


def get_template_for_project(project_path):
    """Получить шаблон для проекта."""
    from FW.parsing.template_loader import get_template_for_project as _get
    return _get(project_path)


def list_templates():
    """Список доступных шаблонов."""
    from FW.parsing.template_loader import list_templates as _list
    return _list()
