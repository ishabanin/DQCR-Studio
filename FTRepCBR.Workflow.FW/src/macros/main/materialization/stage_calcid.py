"""Materialization: Stage with CalcID - workflow_new implementation."""
from typing import TYPE_CHECKING

from FW.logging_config import get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv


logger = get_logger("materialization_stage_calcid")


CALCID_F110 = "RF110.get_base_calc_id()"


def materialization_stage_calcid(
    workflow_new: "WorkflowNewModel",
    obj_key: str,
    obj_type: str,
    env: "BaseMacroEnv"
):
    """Materialization: Stage with CalcID.

    Creates a temporary stage table filtered by CalcID.

    Args:
        workflow_new: WorkflowNewModel
        obj_key: Ключ объекта
        obj_type: Тип объекта ("sql_object" или "parameter")
        env: MacroEnv с API для рендеринга
    """
    if obj_type != "sql_object":
        logger.debug(f"Skipping stage_calcid for {obj_key}: not sql_object")
        return

    sql_obj = workflow_new.sql_objects.get(obj_key)
    if not sql_obj:
        logger.debug(f"Skipping stage_calcid for {obj_key}: not found in sql_objects")
        return

    target_table = workflow_new.target_table

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
            ctx_config = sql_obj.config.get(context, {})
            sql_tools = ctx_config.get("tools", [])
            if sql_tools and tool not in sql_tools:
                continue

            compiled = env.get_compiled("sql_object", obj_key, context, tool)
            if not compiled:
                logger.debug(f"No compiled for {obj_key} [{context}][{tool}]")
                continue

            prepared_sql = compiled.get("prepared_sql", "")
            if not prepared_sql:
                logger.debug(f"No prepared_sql for {obj_key} [{context}][{tool}]")
                continue

            if not prepared_sql.strip():
                continue

            stage_table_name = f"tmp_{sql_obj.name}_{{{{calc_id}}}}"

            distribution_key = None
            # SQLMetadata doesn't have attributes - check config instead
            ctx_config = sql_obj.config.get(context, {})
            if ctx_config and ctx_config.get("attributes"):
                attrs = ctx_config.get("attributes")
                if isinstance(attrs, list):
                    for attr in attrs:
                        if isinstance(attr, dict):
                            dist_key = attr.get("distribution_key")
                            if dist_key is not None:
                                distribution_key = attr.get("name")
                                break

            try:
                rendered = env.render_template(
                    "materialization/stage_calcid",
                    tool=tool,
                    calcid_f110=CALCID_F110,
                    target_table=stage_table_name,
                    sql=prepared_sql,
                    distribution_key=distribution_key
                )
            except Exception as e:
                logger.warning(f"Failed to render stage_calcid with tool {tool}: {e}")
                try:
                    rendered = env.render_template(
                        "materialization/stage_calcid",
                        tool=None,
                        calcid_f110=CALCID_F110,
                        target_table=stage_table_name,
                        sql=prepared_sql,
                        distribution_key=distribution_key
                    )
                except Exception as e2:
                    logger.warning(f"Failed to render stage_calcid with fallback: {e2}")
                    continue
            
            env.update_compiled(
                "sql_object", obj_key, context, tool, "rendered_sql", rendered
            )
            env.update_compiled(
                "sql_object", obj_key, context, tool, "target_table", stage_table_name
            )