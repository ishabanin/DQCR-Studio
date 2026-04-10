"""Materialization: Parameter - workflow_new implementation."""
from typing import TYPE_CHECKING

from FW.logging_config import get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv


logger = get_logger("materialization_param")


DOMAIN_TYPE_MAP = {
    'date': 'date',
    'number': 'numeric',
    'numeric': 'numeric',
    'integer': 'integer',
    'int': 'integer',
}


def materialization_param(
    workflow_new: "WorkflowNewModel",
    obj_key: str,
    obj_type: str,
    env: "BaseMacroEnv"
):
    """Materialization: Parameter.

    Generates SQL for parameter based on its type:
    - dynamic: returns prepared_sql directly (no wrapper)
    - static: renders SQL wrapper (SELECT 'value' FROM DUAL)

    Args:
        workflow_new: WorkflowNewModel
        obj_key: Ключ объекта
        obj_type: Тип объекта ("sql_object" или "parameter")
        env: MacroEnv с API для рендеринга
    """
    if obj_type != "parameter":
        return

    param = workflow_new.parameters.get(obj_key)
    if not param:
        return

    contexts = list(workflow_new.contexts.keys()) if workflow_new.contexts else ["default"]

    for context in contexts:
        context_config = workflow_new.contexts.get(context)
        tools = (
            context_config.tools
            if context_config and context_config.tools
            else workflow_new.tools
            if workflow_new.tools
            else ["adb"]
        )

        for tool in tools:
            compiled = env.get_compiled("parameter", obj_key, context, tool)
            if not compiled:
                continue

            prepared_sql = compiled.get("prepared_sql", "")

            param_value = param.values.get(context)
            if param_value is None and "all" in param.values:
                param_value = param.values.get("all")

            is_dynamic = param_value and param_value.type == "dynamic"

            if is_dynamic:
                env.update_compiled(
                    "parameter", obj_key, context, tool, "rendered_sql", prepared_sql
                )
                env.update_compiled(
                    "parameter", obj_key, context, tool, "target_table", ""
                )
                continue

            p_domain = param.domain_type
            ptype = DOMAIN_TYPE_MAP.get(p_domain, 'text')

            try:
                rendered = env.render_template(
                    "materialization/param",
                    tool=tool,
                    param_model=param,
                    context_name=context,
                    ptype=ptype,
                    param_value=prepared_sql
                )
            except Exception:
                try:
                    rendered = env.render_template(
                        "materialization/param",
                        tool=None,
                        param_model=param,
                        context_name=context,
                        ptype=ptype,
                        param_value=prepared_sql
                    )
                except Exception as e:
                    logger.error(f"Failed to render param: {e}")
                    continue

            env.update_compiled(
                "parameter", obj_key, context, tool, "rendered_sql", rendered
            )
            env.update_compiled(
                "parameter", obj_key, context, tool, "target_table", ""
            )