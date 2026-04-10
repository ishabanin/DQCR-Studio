"""Materialization macro manager для workflow_new.

Обеспечивает:
- Поиск и выполнение Python-макросов материализации
- Tool-specific приоритет (tool -> main)
- Применение к каждому sql_object и parameter для каждого context и tool
"""
from typing import TYPE_CHECKING, Optional

from FW.logging_config import get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv
    from FW.macros import MacroRegistry


logger = get_logger("materialization_macro")


class MaterializationMacroManager:
    """Менеджер для выполнения макросов материализации."""

    def __init__(self, macro_registry: "MacroRegistry"):
        self._macro_registry = macro_registry

    def run_materialization(
        self,
        workflow: "WorkflowNewModel",
        default_materialization: str = "insert_fc"
    ) -> None:
        """Выполнить materialization макросы для всех объектов workflow.

        Для каждого объекта (sql_object/parameter):
        1. Определить materialization тип из config[context]['materialized']
        2. Вызвать соответствующий Python-макрос
        3. Сохранить rendered_sql и target_table в compiled[context][tool]

        Args:
            workflow: WorkflowNewModel
            default_materialization: Тип материализации по умолчанию
        """
        logger.info("Running materialization_macro")

        env = self._create_macro_env(workflow)

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
                self._run_materialization_for_context(
                    env, context, tool, default_materialization
                )

        logger.info("Materialization_macro completed")

    def _create_macro_env(self, workflow: "WorkflowNewModel") -> "BaseMacroEnv":
        """Создать MacroEnv для материализации."""
        from FW.macros.env import BaseMacroEnv

        return BaseMacroEnv(
            workflow=workflow,
            macro_registry=self._macro_registry,
            tools=workflow.tools
        )

    def _run_materialization_for_context(
        self,
        env: "BaseMacroEnv",
        context: str,
        tool: str,
        default_materialization: str
    ) -> None:
        """Выполнить materialization для конкретного контекста и tool.

        Args:
            env: MacroEnv
            context: Имя контекста
            tool: Имя tool
            default_materialization: Тип материализации по умолчанию
        """
        for sql_key, sql_obj in env.get_all_sql_objects().items():
            self._process_sql_object(
                env, sql_key, sql_obj, context, tool, default_materialization
            )

        for param_name, param in env.get_all_parameters().items():
            self._process_parameter(
                env, param_name, param, context, tool
            )

    def _process_sql_object(
        self,
        env: "BaseMacroEnv",
        obj_key: str,
        sql_obj,
        context: str,
        tool: str,
        default_materialization: str
    ) -> None:
        """Обработать SQL объект.

        Args:
            env: MacroEnv
            obj_key: Ключ объекта
            sql_obj: SQLObjectModel
            context: Имя контекста
            tool: Имя tool
            default_materialization: Тип материализации по умолчанию
        """
        ctx_config = sql_obj.config.get(context, {})
        enabled = ctx_config.get("enabled")

        is_enabled = True
        if enabled is not None:
            if isinstance(enabled, dict):
                is_enabled = enabled.get("value", True)
            elif hasattr(enabled, "value"):
                is_enabled = enabled.value
            else:
                is_enabled = enabled

        if not is_enabled:
            return

        if context not in sql_obj.compiled or tool not in sql_obj.compiled.get(context, {}):
            return

        materialized = ctx_config.get("materialization") or ctx_config.get("materialized")
        materialization_type = None

        if materialized is not None:
            if isinstance(materialized, dict):
                materialization_type = materialized.get("value")
            elif hasattr(materialized, "value"):
                materialization_type = materialized.value
            else:
                materialization_type = materialized

        if not materialization_type:
            materialization_type = default_materialization

        if materialization_type == "ephemeral":
            compiled = env.get_compiled("sql_object", obj_key, context, tool)
            if compiled:
                prepared = compiled.get("prepared_sql", "")
                env.update_compiled(
                    "sql_object", obj_key, context, tool, "rendered_sql", prepared
                )
                env.update_compiled(
                    "sql_object", obj_key, context, tool, "target_table", ""
                )
            return

        try:
            macro = self._macro_registry.get_materialization_macro(
                materialization_type, tool
            )
        except Exception as e:
            logger.warning(
                f"Materialization macro '{materialization_type}' not found for tool '{tool}': {e}"
            )
            return


        
        try:
            macro(
                workflow_new=env.workflow,
                obj_key=obj_key,
                obj_type="sql_object",
                env=env
            )
            logger.debug(
                f"Applied materialization '{materialization_type}' to sql_object {obj_key} [{context}][{tool}]"
            )
        except Exception as e:
            import traceback
            logger.error(
                f"Error applying materialization to sql_object {obj_key}: {e}\n{traceback.format_exc()}"
            )

    def _process_parameter(
        self,
        env: "BaseMacroEnv",
        obj_key: str,
        param_obj,
        context: str,
        tool: str
    ) -> None:
        """Обработать параметр.

        Args:
            env: MacroEnv
            obj_key: Имя параметра
            param_obj: ParameterModel
            context: Имя контекста
            tool: Имя tool
        """
        if context not in param_obj.compiled or tool not in param_obj.compiled.get(context, {}):
            return

        try:
            macro = self._macro_registry.get_materialization_macro("param", tool)
        except Exception as e:
            return

        try:
            macro(
                workflow_new=env.workflow,
                obj_key=obj_key,
                obj_type="parameter",
                env=env
            )
            logger.debug(
                f"Applied materialization to parameter {obj_key} [{context}][{tool}]"
            )
        except Exception as e:
            logger.error(
                f"Error applying materialization to parameter {obj_key}: {e}"
            )