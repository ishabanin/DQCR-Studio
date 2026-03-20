"""Materialization: INSERT INTO - Main implementation."""
from typing import TYPE_CHECKING, List

from FW.exceptions.base import BaseFWError

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv


class InsertFcError(BaseFWError):
    """Ошибка материализации insert_fc."""
    pass


def _format_value(default_value, domain_type):
    """Форматировать значение по умолчанию с учётом типа."""
    if default_value is None:
        return None
    
    domain_type_lower = domain_type.lower() if domain_type else "string"
    
    if domain_type_lower in ("string", "date", "timestamp", "datetime"):
        return f"'{default_value}'"
    
    return default_value


def materialization_insert_fc(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    """Materialization: INSERT INTO target_table.
    
    Логика:
    1. Определение target_table_attr_list - атрибуты целевой таблицы, которые:
       - являются ключевыми (is_key=True)
       - являются обязательными (required=True)
       - присутствуют по наименованию в запросе
    
    2. Определение attrs_for_insert:
       - атрибуты из подзапроса (query)
       - + атрибуты из целевой таблицы, которых нет в запросе, но обязательны
       - для обязательных атрибутов подставляется default_value (с учётом типа)
       - особый случай: calcid -> {{CALC_ID}}
    
    Ошибки:
    - В запросе нет ключевых атрибутов
    - В запросе нет обязательного атрибута, для которого не задан default_value
    
    Args:
        step: Workflow шаг с sql_model или param_model
        workflow: Workflow модель
        env: Окружение с API для рендеринга
    """
    if step.sql_model is not None:
        _render_sql(step, workflow, env)
    elif step.param_model is not None:
        _render_param(step, env)


def _build_insert_columns(
    sql_model,
    target_table,
    key_attrs: List[str]
) -> tuple:
    """Построить списки колонок для INSERT.
    
    Логика target_columns:
    1. Ключевой (is_key=True) - добавляется всегда
    2. Обязательный (required=True) - добавляется всегда, если нет в запросе - подставляется default_value
    3. Присутствует в запросе - добавляется если есть в запросе
    
    Returns:
        (target_columns, select_columns)
        - target_columns: колонки для INSERT INTO (...)
        - select_columns: колонки для SELECT (...)
    """
    query_attrs = sql_model.get_attribute_names()
    target_columns = []
    select_columns = []
    
    if target_table and target_table.attributes:
        for attr in target_table.attributes:
            is_key = attr.is_key
            is_in_query = attr.name.lower() in {a.lower() for a in query_attrs}
            is_required = attr.required
            
            should_add_to_target = False
            
            if is_key:
                should_add_to_target = True
            elif is_required:
                should_add_to_target = True
            elif is_in_query:
                should_add_to_target = True
            
            if should_add_to_target:
                target_columns.append(attr.name)
                
                if is_in_query:
                    select_columns.append(attr.name)
                elif is_key and attr.name.lower() == "calcid":
                    select_columns.append("{{CALC_ID}}")
                elif is_key or is_required:
                    default_val = attr.default_value
                    if default_val is not None:
                        formatted_val = _format_value(default_val, attr.domain_type)
                        select_columns.append(f"{formatted_val} as {attr.name}")
                    else:
                        raise InsertFcError(
                            f"Required attribute '{attr.name}' is not present in query "
                            f"and has no default_value defined in target table. "
                            f"Query attributes: {query_attrs}"
                        )
    else:
        for name in query_attrs:
            target_columns.append(name)
            select_columns.append(name)
    
    return target_columns, select_columns


def _render_sql(step: "WorkflowStepModel", workflow: "WorkflowModel", env: "MacroEnv"):
    """Рендеринг для SQL модели."""
    sql_model = step.sql_model
    if sql_model is None:
        return
    
    wf = env.workflow or workflow
    target_table_model = wf.target_table if wf and wf.target_table else None
    
    target_table_name = target_table_model.name if target_table_model else None
    if not target_table_name:
        raise InsertFcError(
            f"Target table name is required for insert_fc. "
            f"Workflow must have target_table defined."
        )
    
    key_attrs = sql_model.get_key_attributes(target_table_model)
    query_attrs = sql_model.get_attribute_names()
    
    if not key_attrs:
        raise InsertFcError(
            f"No key attributes found for insert_fc. "
            f"Query must have key attributes (is_key=True) that exist in target table. "
            f"Query attributes: {query_attrs}, "
            f"Target table primary keys: {target_table_model.primary_key_names if target_table_model else []}"
        )
    
    try:
        target_columns, select_columns = _build_insert_columns(
            sql_model, target_table_model, key_attrs
        )
    except InsertFcError:
        raise
    except Exception as e:
        raise InsertFcError(f"Error building insert columns: {e}")
    
    for tool in env.tools:
        prepared = sql_model.get_prepared_sql(tool)
        
        rendered = env.render_template(
            "materialization/insert_fc_body",
            tool=tool,
            target_table=target_table_name,
            sql=prepared,
            target_columns=target_columns,
            select_columns=select_columns
        )
        
        sql_model.rendered_sql[tool] = rendered


def _render_param(step: "WorkflowStepModel", env: "MacroEnv"):
    """Рендеринг для Parameter модели."""
    param_model = step.param_model
    if param_model is None:
        return
    
    for tool in env.tools:
        prepared = param_model.get_prepared_sql(tool)
        
        rendered = env.render_template(
            "materialization/insert_fc_body",
            tool=tool,
            target_table=param_model.name,
            sql=prepared,
            target_columns=[],
            select_columns=[]
        )
        
        param_model.rendered_sql[tool] = rendered