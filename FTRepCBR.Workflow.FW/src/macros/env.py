"""Macro environment - API для Python-макросов."""
from pathlib import Path
from typing import List, Callable, Any, Optional, TYPE_CHECKING, Dict
from jinja2 import Template

from FW.logging_config import get_logger
from FW.exceptions.base import BaseFWError

if TYPE_CHECKING:
    from FW.macros import MacroRegistry
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel, FolderModel
    from FW.models import ParameterModel
    from FW.materialization.renderer import MaterializationRenderer


logger = get_logger("macro_env")


class WorkflowMacroSecurityError(BaseFWError):
    """Ошибка безопасности - попытка выхода за пределы target директории."""
    pass


class BaseMacroEnv:
    """Базовый класс для макро-окружений.
    
    Содержит общие методы для доступа к workflow.
    """
    
    def __init__(
        self,
        workflow: "WorkflowModel",
        macro_registry: "MacroRegistry",
        tools: List[str],
        **kwargs
    ):
        self._workflow = workflow
        self._macro_registry = macro_registry
        self.tools = tools
    
    @property
    def workflow(self) -> "WorkflowModel":
        """Получить workflow модель."""
        return self._workflow
    
    def get_all_steps(self) -> List["WorkflowStepModel"]:
        """Получить все шаги workflow.
        
        Returns:
            Список всех шагов
        """
        if not self._workflow or not self._workflow.graph:
            return []
        return list(self._workflow.graph.get_all_nodes())
    
    def get_step_by_name(self, full_name: str) -> Optional["WorkflowStepModel"]:
        """Найти шаг по полному имени.
        
        Args:
            full_name: Полное имя шага (напр. "folder/subfolder/step_name")
            
        Returns:
            WorkflowStepModel или None если не найден
        """
        if not self._workflow or not self._workflow.graph:
            return None
        
        for step in self._workflow.graph.get_all_nodes():
            if step.full_name == full_name:
                return step
        return None
    
    def get_steps_in_folder(self, folder: str) -> List["WorkflowStepModel"]:
        """Получить все шаги в указанной папке.
        
        Args:
            folder: Путь к папке (напр. "001_Load" или "root")
            
        Returns:
            Список шагов в папке
        """
        if not self._workflow or not self._workflow.graph:
            return []
        
        folder_normalized = folder.rstrip("/")
        result = []
        for step in self._workflow.graph.get_all_nodes():
            step_folder = step.folder.rstrip("/") if step.folder else "root"
            if step_folder == folder_normalized:
                result.append(step)
        return result
    
    def get_project_prop(self, name: str, default: Any = None) -> Any:
        """Получить значение свойства проекта.
        
        Args:
            name: Имя свойства
            default: Значение по умолчанию, если свойство не найдено
            
        Returns:
            Значение свойства или default
        """
        if self._workflow and self._workflow.project_properties:
            return self._workflow.project_properties.get(name, default)
        return default


class MacroEnv(BaseMacroEnv):
    """Окружение для выполнения Python-макросов.
    
    Предоставляет API для:
    - Рендеринга jinja2 шаблонов
    - Добавления шагов в workflow
    """
    
    def __init__(
        self,
        renderer: "MaterializationRenderer",
        macro_registry: "MacroRegistry",
        workflow: "WorkflowModel",
        tools: List[str],
        step: Optional["WorkflowStepModel"] = None,
        param_model: Optional["ParameterModel"] = None,
        folder_path: Optional[str] = None,
        folder_steps: Optional[List["WorkflowStepModel"]] = None,
        steps: Optional[List["WorkflowStepModel"]] = None,
        context_name: Optional[str] = None,
        flags: Optional[Dict[str, Any]] = None,
        constants: Optional[Dict[str, Any]] = None,
        folder: Optional["FolderModel"] = None
    ):
        super().__init__(workflow, macro_registry, tools)
        self._renderer = renderer
        self.step = step
        self.param_model = param_model
        self.folder_path = folder_path
        self.folder_steps = folder_steps or []
        self.steps = steps
        self._context_name = context_name
        self._flags = flags or {}
        self._constants = constants or {}
        self.folder = folder
    
    @property
    def context_name(self) -> Optional[str]:
        """Имя активного контекста."""
        return self._context_name
    
    @property
    def flags(self) -> Dict[str, Any]:
        """Словарь флагов контекста."""
        return self._flags
    
    @property
    def constants(self) -> Dict[str, Any]:
        """Словарь констант контекста."""
        return self._constants
    
    def get_flag(self, key: str, default: Any = None) -> Any:
        """Получить значение флага по ключу (поддержка вложенных через точку).
        
        Args:
            key: Ключ (напр. 'overduecalcmethod.fifo')
            default: Значение по умолчанию
            
        Returns:
            Значение флага
        """
        parts = key.split(".")
        value = self._flags
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_constant(self, key: str, default: Any = None) -> Any:
        """Получить значение константы по ключу.
        
        Args:
            key: Ключ константы
            default: Значение по умолчанию
            
        Returns:
            Значение константы
        """
        return self._constants.get(key, default)
    
    def render_template(self, template_name: str, tool: str, **kwargs) -> str:
        """Рендерит jinja2 шаблон для указанного tool.
        
        Логика поиска:
        1. <tool>/<name>
        2. <tool>/**/<name> (рекурсивно)
        3. main/<name> (fallback)
        
        Args:
            template_name: Имя шаблона (напр. materialization/insert_fc_body)
            tool: Целевой tool (oracle/adb/postgresql)
            **kwargs: Переменные для подстановки в шаблон
            
        Returns:
            Отрендеренный текст
        """
        try:
            content = self._macro_registry.get_macro_content(template_name, tool)
            logger.debug(f"Got template content: {len(content)} chars for {template_name}@{tool}")
        except Exception as e:
            logger.debug(f"Failed to get {template_name}@{tool}: {e}, trying main")
            content = self._macro_registry.get_macro_content(template_name, None)
        
        template = Template(content, trim_blocks=True, lstrip_blocks=True)
        
        try:
            params = dict(kwargs)
            params["tool"] = tool
            params["ctx"] = {
                "flags": self._flags,
                "constants": self._constants,
                "context_name": self._context_name
            }
            result = template.render(params)
            logger.debug(f"Template rendered: {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"Template render error: {e}")
            raise
    
    def add_step(self, step: "WorkflowStepModel"):
        """Добавляет шаг в workflow.
        
        Приоритет:
        1. self.steps (список) - если передан
        2. self.workflow.graph - для совместимости
        
        Args:
            step: Шаг для добавления
        """
        if self.steps is not None:
            self.steps.append(step)
            logger.debug(f"Added step '{step.step_id}' to steps list")
        elif self.workflow.graph is not None:
            self.workflow.graph.add_node(step)
            logger.debug(f"Added step '{step.step_id}' to workflow graph")
    
    def add_steps(self, steps: List["WorkflowStepModel"]):
        """Добавляет несколько шагов в workflow.
        
        Args:
            steps: Список шагов для добавления
        """
        for step in steps:
            self.add_step(step)
    
    def get_step_by_name(self, full_name: str) -> Optional["WorkflowStepModel"]:
        """Найти шаг по полному имени.
        
        Приоритет поиска:
        1. self.steps (список)
        2. self.workflow.graph
        
        Args:
            full_name: Полное имя шага (напр. "folder/subfolder/step_name")
            
        Returns:
            WorkflowStepModel или None если не найден
        """
        # Сначала ищем в steps (списке)
        if self.steps:
            for step in self.steps:
                if step.full_name == full_name:
                    return step
        
        # Потом в graph
        if self.workflow and self.workflow.graph:
            for step in self.workflow.graph.get_all_nodes():
                if step.full_name == full_name:
                    return step
        return None
    
    def regenerate_param(self, param_model: "ParameterModel", context: str = "all") -> None:
        """Перегенерировать prepared_sql для параметра для всех tools.
        
        Args:
            param_model: Модель параметра
            context: Имя контекста
        """
        for tool in self.tools:
            if param_model.is_dynamic(context):
                source_sql = param_model.get_value(context) or ""
                sql = self._renderer._replace_functions_from_sql(source_sql, tool)
                param_model.prepared_sql[tool] = sql
                param_model.rendered_sql[tool] = sql
                logger.debug(f"Regenerated prepared_sql for param '{param_model.name}' tool '{tool}': {len(sql)} chars")
    
    def refresh_step_metadata(self, step: "WorkflowStepModel") -> None:
        """Пересоздать metadata для шага на основе prepared_sql.
        
        Args:
            step: Шаг workflow для обновления metadata
        """
        from FW.parsing.sql_metadata import SQLMetadata, SQLMetadataParser
        
        parser = SQLMetadataParser()
        
        if step.sql_model and step.sql_model.prepared_sql:
            tool = list(step.sql_model.prepared_sql.keys())[0]
            sql_content = step.sql_model.prepared_sql.get(tool, "")
            
            if sql_content:
                metadata = step.sql_model.metadata
                metadata.parameters = parser.extract_parameters(sql_content, set())
                metadata.tables = parser.extract_tables(sql_content, set())
                # model_refs не перезаписываем - там хранятся исходные ссылки из SQL
                
        elif step.param_model and step.param_model.prepared_sql:
            tool = list(step.param_model.prepared_sql.keys())[0]
            sql_content = step.param_model.prepared_sql.get(tool, "")
            
            if sql_content:
                metadata = SQLMetadata()
                metadata.parameters = parser.extract_parameters(sql_content, set())
                step.param_model._dynamic_params = metadata.parameters
        
        logger.debug(f"Refreshed metadata for step '{step.name}'")


class WorkflowMacroEnv(BaseMacroEnv):
    """Окружение для генерации workflow файлов.
    
    Позволяет создавать файлы и директории внутри target/<engine>/<workflow_name>/
    Безопасность: нельзя выйти за пределы target директории через ../
    """
    
    def __init__(
        self,
        workflow: "WorkflowModel",
        macro_registry: "MacroRegistry",
        target_path: Path,
        tools: List[str]
    ):
        super().__init__(workflow, macro_registry, tools)
        self._target_path = target_path.resolve()
        self._created_files: List[Path] = []
        
        self._target_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def target_path(self) -> Path:
        """Target directory (read-only).
        
        Returns:
            Путь к директории target/<engine>/<workflow_name>/
        """
        return self._target_path
    
    @property
    def workflow_name(self) -> str:
        """Имя workflow."""
        return self.workflow.model_name if self.workflow else "unknown"
    
    def _validate_path(self, relative_path: str) -> Path:
        """Валидировать что путь внутри target_path.
        
        Args:
            relative_path: Относительный путь
            
        Returns:
            Нормализованный абсолютный путь
            
        Raises:
            WorkflowMacroSecurityError: Если путь выходит за пределы target_path
        """
        if not relative_path:
            raise WorkflowMacroSecurityError("Path cannot be empty")
        
        normalized = (self._target_path / relative_path).resolve()
        
        try:
            normalized.relative_to(self._target_path)
        except ValueError:
            raise WorkflowMacroSecurityError(
                f"Path '{relative_path}' escapes target directory '{self._target_path}'. "
                f"Use only relative paths inside the target directory."
            )
        
        return normalized
    
    def render_template(self, template_name: str, tool: str, **kwargs) -> str:
        """Рендерит jinja2 шаблон для workflow.
        
        Логика поиска шаблона:
        1. workflow/<engine>/templates/<name>
        2. <engine>/templates/<name>
        3. workflow/<engine>/<name>
        4. <engine>/<name>
        5. main/<name>
        
        Args:
            template_name: Имя шаблона (напр. "dag", "task")
            tool: Целевой workflow engine (airflow, dbt, oracle_plsql)
            **kwargs: Переменные для подстановки в шаблон
            
        Returns:
            Отрендеренный текст
        """
        content = None
        engine = tool
        
        search_paths = [
            "dag",  # Short name - directly by name
            f"workflow/{engine}/templates/{template_name}",
            f"{engine}/templates/{template_name}",
            f"workflow/{engine}/{template_name}",
            f"{engine}/{template_name}",
            f"workflow/main/{template_name}",
            f"main/{template_name}",
        ]
        
        for path in search_paths:
            try:
                # Normalize: убираем префикс workflow/<engine>/templates/ если он есть
                # Ключи в _macros хранятся как 'airflow/templates/dag', а не 'workflow/airflow/templates/dag'
                if self._macro_registry.has_macro(path, engine):
                    content = self._macro_registry.get_macro_content(path, engine)
                    logger.debug(f"Found template: {path} (tool={engine})")
                    break
                # Fallback: попробовать найти по короткому имени
                if '/' not in path:
                    # path это просто 'dag', ищем через has_macro с tool=engine
                    if self._macro_registry.has_macro(path, engine):
                        content = self._macro_registry.get_macro_content(path, engine)
                        logger.debug(f"Found template by short name: {path} (tool={engine})")
                        break
            except Exception as e:
                logger.debug(f"Failed to get {path}: {e}")
        
        if content is None:
            raise FileNotFoundError(
                f"Template '{template_name}' not found for engine '{engine}'. "
                f"Searched: {search_paths}"
            )
        
        template = Template(content, trim_blocks=True, lstrip_blocks=True)
        
        params = dict(kwargs)
        params["tool"] = tool
        params["workflow"] = self.workflow
        result = template.render(params)
        
        logger.debug(f"Template '{template_name}' rendered: {len(result)} chars")
        return result
    
    def create_file(self, relative_path: str, content: str, encoding: str = "utf-8") -> Path:
        """Создать файл внутри target директории.
        
        Args:
            relative_path: Путь относительно target_path (напр. "dags/dag.py")
            content: Содержимое файла
            encoding: Кодировка файла
            
        Returns:
            Полный путь к созданному файлу
            
        Raises:
            WorkflowMacroSecurityError: Если путь выходит за пределы target_path
        """
        file_path = self._validate_path(relative_path)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        
        self._created_files.append(file_path)
        logger.debug(f"Created file: {file_path}")
        
        return file_path
    
    def create_directory(self, name: str) -> "WorkflowMacroEnv":
        """Создать поддиректорию и вернуть новый env для неё.
        
        Args:
            name: Имя директории (напр. "dags" или "subfolder/tasks")
            
        Returns:
            Новый WorkflowMacroEnv с обновлённым target_path
        """
        new_target = self._validate_path(name)
        new_target.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Created directory: {new_target}")
        
        return WorkflowMacroEnv(
            workflow=self.workflow,
            macro_registry=self._macro_registry,
            target_path=new_target,
            tools=self.tools
        )
    
    def list_created_files(self) -> List[Path]:
        """Список созданных файлов.
        
        Returns:
            Список абсолютных путей к созданным файлам
        """
        return self._created_files.copy()
