"""Macro environment для workflow_new."""

from pathlib import Path
from typing import List, Callable, Any, Optional, TYPE_CHECKING, Dict
from jinja2 import Template

from FW.logging_config import get_logger
from FW.exceptions.base import BaseFWError
import FW.config as cfg

if TYPE_CHECKING:
    from FW.macros import MacroRegistry
    from FW.models.workflow_new import WorkflowNewModel
    from FW.models.sql_object import SQLObjectModel
    from FW.models.parameter import ParameterModel


logger = get_logger("macro_env")


class MacroEnvError(BaseFWError):
    """Ошибка работы с MacroEnv."""

    pass


class BaseMacroEnv:
    """Базовый класс для макро-окружений.

    Содержит общие методы для доступа к workflow_new.
    """

    def __init__(
        self,
        workflow: "WorkflowNewModel",
        macro_registry: "MacroRegistry",
        tools: List[str],
    ):
        self._workflow = workflow
        self._macro_registry = macro_registry
        self.tools = tools
        t = cfg.ToolRegistry()        
        self.toolsConfig = t.toolsConfig

    @property
    def workflow(self) -> "WorkflowNewModel":
        """Получить workflow модель."""
        return self._workflow

    def get_sql_object(self, key: str) -> Optional["SQLObjectModel"]:
        """Получить SQL объект по ключу.

        Args:
            key: Ключ объекта (путь к SQL файлу)

        Returns:
            SQLObjectModel или None
        """
        if not self._workflow:
            return None
        return self._workflow.sql_objects.get(key)

    def get_toolDataTypeByDomainType(self, tool, domain_type) -> str:
        type = self.toolsConfig[tool].domain2basetype.get(domain_type)
        if type:
           return type.get("basetype")

    def get_all_sql_objects(self) -> Dict[str, "SQLObjectModel"]:
        """Получить все SQL объекты.

        Returns:
            Словарь SQLObjectModel
        """
        if not self._workflow:
            return {}
        return self._workflow.sql_objects

    def get_parameter(self, name: str) -> Optional["ParameterModel"]:
        """Получить параметр по имени.

        Args:
            name: Имя параметра

        Returns:
            ParameterModel или None
        """
        if not self._workflow:
            return None
        return self._workflow.parameters.get(name)

    def get_all_parameters(self) -> Dict[str, "ParameterModel"]:
        """Получить все параметры.

        Returns:
            Словарь ParameterModel
        """
        if not self._workflow:
            return {}
        return self._workflow.parameters

    def add_parameter(self, param: "ParameterModel") -> None:
        """Добавить параметр в workflow.

        Args:
            param: Параметр для добавления
        """
        if not self._workflow:
            raise MacroEnvError("Workflow not set")

        self._workflow.parameters[param.name] = param
        logger.debug(f"Added parameter '{param.name}' to workflow")

    def update_compiled(
        self,
        obj_type: str,
        obj_key: str,
        context: str,
        tool: str,
        field: str,
        value: Any,
    ) -> None:
        """Обновить поле в compiled структуре объекта.

        Args:
            obj_type: Тип объекта ('sql_object' или 'parameter')
            obj_key: Ключ объекта
            context: Имя контекста
            tool: Имя tool
            field: Имя поля в compiled
            value: Значение поля
        """
        if not self._workflow:
            raise MacroEnvError("Workflow not set")

        obj = None
        if obj_type == "sql_object":
            obj = self._workflow.sql_objects.get(obj_key)
        elif obj_type == "parameter":
            obj = self._workflow.parameters.get(obj_key)

        if not obj:
            logger.warning(f"Object not found: {obj_type}.{obj_key}")
            return

        if context not in obj.compiled:
            obj.compiled[context] = {}
        if tool not in obj.compiled[context]:
            obj.compiled[context][tool] = {}

        obj.compiled[context][tool][field] = value
        logger.debug(
            f"Updated compiled[{obj_type}.{obj_key}][{context}][{tool}].{field}"
        )

    def get_compiled(
        self, obj_type: str, obj_key: str, context: str, tool: str
    ) -> Optional[Dict[str, Any]]:
        """Получить compiled данные для объекта.

        Args:
            obj_type: Тип объекта ('sql_object' или 'parameter')
            obj_key: Ключ объекта
            context: Имя контекста
            tool: Имя tool

        Returns:
            Словарь compiled или None
        """
        if not self._workflow:
            return None

        obj = None
        if obj_type == "sql_object":
            obj = self._workflow.sql_objects.get(obj_key)
        elif obj_type == "parameter":
            obj = self._workflow.parameters.get(obj_key)

        if not obj:
            return None

        return obj.compiled.get(context, {}).get(tool)

    def has_step_in_graph(self, obj_key: str, context: str, tool: str) -> bool:
        """Проверить, есть ли шаг в графе.

        Args:
            obj_key: Ключ объекта
            context: Имя контекста
            tool: Имя tool

        Returns:
            True если шаг существует
        """
        if not self._workflow or not self._workflow.graph:
            return False

        graph_ctx = self._workflow.graph.get(context)
        if not graph_ctx:
            return False

        graph_tool = graph_ctx.get(tool)
        if not graph_tool:
            return False

        return obj_key in graph_tool.get("steps", {})

    def add_step_to_graph(
        self,
        obj_type: str,
        obj_key: str,
        context: str,
        tool: str,
        step_scope: Optional[str] = None,
    ) -> None:
        """Добавить шаг в граф workflow.

        Args:
            obj_type: Тип объекта ('sql_object' или 'parameter')
            obj_key: Ключ объекта
            context: Имя контекста
            tool: Имя tool
            step_scope: Область шага (для параметров: 'param' или 'flag')
        """
        if not self._workflow or not self._workflow.graph:
            raise MacroEnvError("Workflow graph not set")

        if context not in self._workflow.graph:
            self._workflow.graph[context] = {}
        if tool not in self._workflow.graph[context]:
            self._workflow.graph[context][tool] = {"steps": {}, "edges": []}

        steps = self._workflow.graph[context][tool]["steps"]

        if obj_key in steps:
            logger.debug(f"Step {obj_key} already exists in graph")
            return

        if obj_type == "sql_object":
            steps[obj_key] = {
                "context": context,
                "tool": tool,
                "step_type": "sql",
                "step_scope": "sql",
                "object_id": obj_key,
                "asynch": False,
            }
        elif obj_type == "parameter":
            param = self._workflow.parameters.get(obj_key)
            domain_type = param.domain_type if param else "string"
            scope = step_scope or ("flag" if domain_type == "bool" else "param")
            steps[obj_key] = {
                "context": context,
                "tool": tool,
                "step_type": "param",
                "step_scope": scope,
                "object_id": obj_key,
                "asynch": False,
            }

        logger.debug(f"Added step '{obj_key}' to graph [{context}][{tool}]")

    def render_template(self, template_name: str, tool: str, **kwargs) -> str:
        """Рендерит jinja2 шаблон для указанного tool.

        Логика поиска:
        1. <tool>/<name>
        2. main/<name> (fallback)

        Args:
            template_name: Имя шаблона (напр. materialization/insert_fc_body)
            tool: Целевой tool (oracle/adb/postgresql)
            **kwargs: Переменные для подстановки в шаблон

        Returns:
            Отрендеренный текст
        """
        try:
            content = self._macro_registry.get_macro_content(template_name, tool)
        except Exception as e:
            logger.debug(f"Failed to get {template_name}@{tool}: {e}, trying main")
            content = self._macro_registry.get_macro_content(template_name, None)

        template = Template(content, trim_blocks=True, lstrip_blocks=True)

        params = dict(kwargs)
        params["tool"] = tool
        result = template.render(params)

        logger.debug(f"Template rendered: {len(result)} chars")
        return result

    def get_project_prop(self, name: str, default: Any = None) -> Any:
        """Получить значение свойства проекта.

        Args:
            name: Имя свойства
            default: Значение по умолчанию

        Returns:
            Значение свойства или default
        """
        if self._workflow and self._workflow.project:
            return self._workflow.project.project_properties.get(name, default)
        return default


class WorkflowMacroManager:
    """Менеджер для выполнения макросов workflow.

    Обеспечивает:
    - Поиск и выполнение Python-макросов
    - Tool-specific приоритет (tool -> main)
    - Model reference resolution
    """

    def __init__(self, macro_registry: "MacroRegistry"):
        self._macro_registry = macro_registry

    def run_model_ref(
        self, workflow: "WorkflowNewModel", model_ref_macro_name: str
    ) -> None:
        """Выполнить model_ref макрос для всех объектов workflow.

        Args:
            workflow: WorkflowNewModel
            model_ref_macro_name: Имя макроса (напр. 'table')
        """
        logger.info(f"Running model_ref macro: {model_ref_macro_name}")

        env = BaseMacroEnv(
            workflow=workflow, macro_registry=self._macro_registry, tools=workflow.tools
        )

        contexts = list(workflow.contexts.keys()) if workflow.contexts else ["default"]

        for context in contexts:
            context_config = workflow.contexts.get(context)
            tools = (
                context_config.tools
                if context_config and context_config.tools
                else workflow.tools
                if workflow.tools
                else ["adb"]
            )

            for tool in tools:
                self._run_model_ref_for_context(
                    env, model_ref_macro_name, context, tool
                )

        logger.info(f"Model_ref macro completed")

    def _run_model_ref_for_context(
        self, env: BaseMacroEnv, model_ref_macro_name: str, context: str, tool: str
    ) -> None:
        """Выполнить model_ref для конкретного контекста и tool.

        Args:
            env: MacroEnv
            model_ref_macro_name: Имя макроса
            context: Имя контекста
            tool: Имя tool
        """
        try:
            macro = self._macro_registry.get_model_ref_macro(model_ref_macro_name, tool)
        except Exception as e:
            logger.warning(
                f"Model_ref macro '{model_ref_macro_name}' not found for tool '{tool}': {e}"
            )
            return

        for sql_key, sql_obj in env.get_all_sql_objects().items():
            ctx_config = sql_obj.config.get(context, {})
            enabled = ctx_config.get("enabled")
            is_enabled = True
            if enabled is not None:
                if hasattr(enabled, "value"):
                    is_enabled = enabled.value
                else:
                    is_enabled = enabled

            if not is_enabled:
                continue

            if context not in sql_obj.compiled or tool not in sql_obj.compiled.get(
                context, {}
            ):
                continue

            metadata = sql_obj.metadata
            if not metadata or not metadata.model_refs:
                continue

            for ref_full, ref_info in metadata.model_refs.items():
                try:
                    path = ref_info.get("path", ref_full)
                    replacement = macro(
                        path,
                        tool,
                        context,
                        env.workflow,
                        env,
                        obj_type="sql_object",
                        obj_key=sql_key,
                    )

                    current_compiled = env.get_compiled(
                        "sql_object", sql_key, context, tool
                    )
                    if current_compiled is None:
                        env.update_compiled(
                            "sql_object",
                            sql_key,
                            context,
                            tool,
                            "prepared_sql",
                            sql_obj.source_sql,
                        )
                        current_compiled = env.get_compiled(
                            "sql_object", sql_key, context, tool
                        )

                    prepared_sql = (
                        current_compiled.get("prepared_sql", sql_obj.source_sql)
                        if current_compiled
                        else sql_obj.source_sql
                    )
                    prepared_sql = prepared_sql.replace(ref_full, replacement)

                    env.update_compiled(
                        "sql_object",
                        sql_key,
                        context,
                        tool,
                        "prepared_sql",
                        prepared_sql,
                    )

                    model_refs = (
                        current_compiled.get("model_refs", {})
                        if current_compiled
                        else {}
                    )
                    model_refs[ref_full] = replacement
                    env.update_compiled(
                        "sql_object", sql_key, context, tool, "model_refs", model_refs
                    )

                    logger.debug(f"Replaced {ref_full} -> {replacement} in {sql_key}")
                except Exception as e:
                    logger.error(
                        f"Error resolving model_ref {ref_full} in {sql_key}: {e}"
                    )

        for param_name, param in env.get_all_parameters().items():
            if context not in param.compiled or tool not in param.compiled.get(
                context, {}
            ):
                continue

            param_value = param.values.get(context)
            if param_value is None and "all" in param.values:
                param_value = param.values.get("all")

            if param_value is None:
                continue

            metadata = param.metadata
            if not metadata or not metadata.model_refs:
                continue

            for ref_full, ref_info in metadata.model_refs.items():
                try:
                    path = ref_info.get("path", ref_full)
                    replacement = macro(
                        path,
                        tool,
                        context,
                        env.workflow,
                        env,
                        obj_type="parameter",
                        obj_key=param_name,
                    )

                    current_compiled = env.get_compiled(
                        "parameter", param_name, context, tool
                    )
                    if current_compiled is None:
                        param_type = param_value.type if param_value else "static"
                        source_sql = (
                            param_value.value if param_type == "dynamic" else ""
                        )
                        env.update_compiled(
                            "parameter",
                            param_name,
                            context,
                            tool,
                            "prepared_sql",
                            source_sql,
                        )
                        current_compiled = env.get_compiled(
                            "parameter", param_name, context, tool
                        )

                    prepared_sql = (
                        current_compiled.get("prepared_sql", "")
                        if current_compiled
                        else ""
                    )
                    if prepared_sql:
                        prepared_sql = prepared_sql.replace(ref_full, replacement)
                        env.update_compiled(
                            "parameter",
                            param_name,
                            context,
                            tool,
                            "prepared_sql",
                            prepared_sql,
                        )

                    model_refs = (
                        current_compiled.get("model_refs", {})
                        if current_compiled
                        else {}
                    )
                    model_refs[ref_full] = replacement
                    env.update_compiled(
                        "parameter", param_name, context, tool, "model_refs", model_refs
                    )

                    logger.debug(
                        f"Replaced {ref_full} -> {replacement} in param {param_name}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error resolving model_ref {ref_full} in param {param_name}: {e}"
                    )

    def run_parameter_macro(
        self, workflow: "WorkflowNewModel", parameter_macro_name: str
    ) -> None:
        """Выполнить parameter_macro для всех параметров workflow.

        Генерирует prepared_sql для каждого параметра на основе его типа.

        Args:
            workflow: WorkflowNewModel
            parameter_macro_name: Имя макроса (напр. 'param')
        """
        logger.info(f"Running parameter_macro: {parameter_macro_name}")

        env = BaseMacroEnv(
            workflow=workflow, macro_registry=self._macro_registry, tools=workflow.tools
        )

        contexts = list(workflow.contexts.keys()) if workflow.contexts else ["default"]

        for context in contexts:
            context_config = workflow.contexts.get(context)
            tools = (
                context_config.tools
                if context_config and context_config.tools
                else workflow.tools
                if workflow.tools
                else ["adb"]
            )

            for tool in tools:
                self._run_parameter_macro_for_context(
                    env, parameter_macro_name, context, tool
                )

        logger.info(f"Parameter_macro completed")

    def _run_parameter_macro_for_context(
        self, env: BaseMacroEnv, parameter_macro_name: str, context: str, tool: str
    ) -> None:
        """Выполнить parameter_macro для конкретного контекста и tool.

        Args:
            env: MacroEnv
            parameter_macro_name: Имя макроса
            context: Имя контекста
            tool: Имя tool
        """
        try:
            macro = self._macro_registry.get_parameter_macro(parameter_macro_name, tool)
        except Exception as e:
            logger.warning(
                f"Parameter macro '{parameter_macro_name}' not found for tool '{tool}': {e}"
            )
            return

        for param_name, param in env.get_all_parameters().items():
            if context not in param.compiled or tool not in param.compiled.get(
                context, {}
            ):
                continue

            param_value = param.values.get(context)
            if param_value is None and "all" in param.values:
                param_value = param.values.get("all")

            if param_value is None:
                continue

            try:
                prepared_sql = macro(
                    param_model=param,
                    tool=tool,
                    context=context,
                    workflow_new=env.workflow,
                    env=env,
                )

                env.update_compiled(
                    "parameter", param_name, context, tool, "prepared_sql", prepared_sql
                )

                logger.debug(
                    f"Generated prepared_sql for param {param_name} [{context}][{tool}]: {len(prepared_sql)} chars"
                )
            except Exception as e:
                logger.error(
                    f"Error generating prepared_sql for param {param_name}: {e}"
                )

    def run_functions_macro(self, workflow: "WorkflowNewModel") -> None:
        """Выполнить function macros для всех объектов workflow.

        Применяет функции из macros/functions к SQL объектам и параметрам.

        Args:
            workflow: WorkflowNewModel
        """
        logger.info("Running functions_macro")

        from FW.macros.main.functions.functions_macro import (
            apply_all_functions_to_object,
            apply_all_functions_to_parameter,
        )

        env = BaseMacroEnv(
            workflow=workflow, macro_registry=self._macro_registry, tools=workflow.tools
        )

        contexts = list(workflow.contexts.keys()) if workflow.contexts else ["default"]

        for context in contexts:
            context_config = workflow.contexts.get(context)
            tools = (
                context_config.tools
                if context_config and context_config.tools
                else workflow.tools
                if workflow.tools
                else ["adb"]
            )

            for tool in tools:
                self._run_functions_for_context(
                    env,
                    apply_all_functions_to_object,
                    apply_all_functions_to_parameter,
                    context,
                    tool,
                )

        logger.info("Functions_macro completed")

    def _run_functions_for_context(
        self,
        env: BaseMacroEnv,
        apply_to_object_func,
        apply_to_param_func,
        context: str,
        tool: str,
    ) -> None:
        """Выполнить function macros для конкретного контекста и tool.

        Args:
            env: MacroEnv
            apply_to_object_func: Функция для применения к SQL объектам
            apply_to_param_func: Функция для применения к параметрам
            context: Имя контекста
            tool: Имя tool
        """
        for sql_key, sql_obj in env.get_all_sql_objects().items():
            ctx_config = sql_obj.config.get(context, {})
            enabled = ctx_config.get("enabled")
            is_enabled = True
            if enabled is not None:
                if hasattr(enabled, "value"):
                    is_enabled = enabled.value
                else:
                    is_enabled = enabled

            if not is_enabled:
                continue

            if context not in sql_obj.compiled or tool not in sql_obj.compiled.get(
                context, {}
            ):
                continue

            try:
                prepared_sql = apply_to_object_func(
                    sql_obj=sql_obj,
                    tool=tool,
                    context=context,
                    workflow_new=env.workflow,
                    env=env,
                    obj_type="sql_object",
                    obj_key=sql_key,
                )

                if prepared_sql:
                    env.update_compiled(
                        "sql_object",
                        sql_key,
                        context,
                        tool,
                        "prepared_sql",
                        prepared_sql,
                    )
                    logger.debug(
                        f"Applied functions to sql_object {sql_key} [{context}][{tool}]"
                    )
            except Exception as e:
                logger.error(f"Error applying functions to sql_object {sql_key}: {e}")

        for param_name, param in env.get_all_parameters().items():
            if context not in param.compiled or tool not in param.compiled.get(
                context, {}
            ):
                continue

            try:
                prepared_sql = apply_to_param_func(
                    param_obj=param,
                    tool=tool,
                    context=context,
                    workflow_new=env.workflow,
                    env=env,
                    obj_type="parameter",
                    obj_key=param_name,
                )

                if prepared_sql:
                    env.update_compiled(
                        "parameter",
                        param_name,
                        context,
                        tool,
                        "prepared_sql",
                        prepared_sql,
                    )
                    logger.debug(
                        f"Applied functions to parameter {param_name} [{context}][{tool}]"
                    )
            except Exception as e:
                logger.error(f"Error applying functions to parameter {param_name}: {e}")

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
