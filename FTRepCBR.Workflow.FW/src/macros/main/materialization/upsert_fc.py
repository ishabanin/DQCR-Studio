"""Materialization: UPSERT (MERGE/UPDATE) - Main implementation."""
from typing import TYPE_CHECKING, List

from FW.exceptions.base import BaseFWError

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv


class UpsertFcError(BaseFWError):
    """Ошибка материализации upsert_fc."""
    pass


def materialization_upsert_fc(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    """Materialization: UPSERT (MERGE/UPDATE) into target_table.
    
    Логика:
    1. Определение ключевых атрибутов (для JOIN):
       - sql_model.attributes с is_key=True
       - иначе target_table.primary_keys
    2. Определение полей для UPDATE:
       - все атрибуты sql_model, кроме ключевых
       - фильтр: только те, что есть в target_table
       - ЕСЛИ ПУСТО -> raise UpsertFcError
    
    Args:
        step: Workflow шаг с sql_model или param_model
        workflow: Workflow модель
        env: Окружение с API для рендеринга
    """
    if step.sql_model is not None:
        _render_sql(step, workflow, env)
    elif step.param_model is not None:
        _render_param(step, env)


def _render_sql(step: "WorkflowStepModel", workflow: "WorkflowModel", env: "MacroEnv"):
    """Рендеринг для SQL модели."""
    sql_model = step.sql_model
    if sql_model is None:
        return
    
    wf = env.workflow or workflow
    target_table_model = wf.target_table if wf and wf.target_table else None
    
    target_table_name = target_table_model.name if target_table_model else None
    if not target_table_name:
        raise UpsertFcError(
            f"Target table name is required for upsert_fc. "
            f"Workflow must have target_table defined."
        )
    
    key_attrs = sql_model.get_key_attributes(target_table_model)
    update_attrs = sql_model.get_update_attributes(target_table_model, key_attrs)
    
    attr_names = []
    if sql_model.attributes:
        attr_names = [a.name for a in sql_model.attributes]
    elif sql_model.metadata and sql_model.metadata.aliases:
        attr_names = [a.get('alias', '') for a in sql_model.metadata.aliases if isinstance(a, dict)]
    
    if not update_attrs:
        raise UpsertFcError(
            f"No update columns defined for upsert_fc. "
            f"Query must have non-key attributes that exist in target table. "
            f"Key attributes: {key_attrs}, "
            f"Query attributes: {attr_names}"
        )
    
    calc_id_literal = "{{CALC_ID}}"
    
    for tool in env.tools:
        prepared = sql_model.get_prepared_sql(tool)
        
        rendered = env.render_template(
            "materialization/upsert_fc_body",
            tool=tool,
            target_table=target_table_name,
            sql=prepared,
            pk_columns=key_attrs,
            update_columns=update_attrs,
            calc_id_literal=calc_id_literal
        )
        
        sql_model.rendered_sql[tool] = rendered


def _render_param(step: "WorkflowStepModel", env: "MacroEnv"):
    """Рендеринг для Parameter модели."""
    param_model = step.param_model
    if param_model is None:
        return
    
    calc_id_literal = "{{CALC_ID}}"
    
    for tool in env.tools:
        prepared = param_model.get_prepared_sql(tool)
        
        rendered = env.render_template(
            "materialization/upsert_fc_body",
            tool=tool,
            target_table=param_model.name,
            sql=prepared,
            pk_columns=[],
            update_columns=[],
            calc_id_literal=calc_id_literal
        )
        
        param_model.rendered_sql[tool] = rendered
