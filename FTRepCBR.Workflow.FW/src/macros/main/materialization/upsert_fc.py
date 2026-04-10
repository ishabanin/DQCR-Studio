"""Materialization: UPSERT (MERGE/UPDATE) - workflow_new implementation."""
from typing import TYPE_CHECKING, List, Optional
import traceback

from FW.exceptions.base import BaseFWError

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv


class UpsertFcError(BaseFWError):
    """Ошибка материализации upsert_fc."""
    pass


def _format_value(default_value, domain_type):
    """Форматировать значение по умолчанию с учётом типа."""
    if default_value is None:
        return None
    
    domain_type_lower = domain_type.lower() if domain_type else "string"
    
    if domain_type_lower in ("string", "date", "timestamp", "datetime"):
        return f"'{default_value}'"
    
    return default_value


def materialization_upsert_fc(
    workflow_new: "WorkflowNewModel",
    obj_key: str,
    obj_type: str,
    env: "BaseMacroEnv"
):
    """Materialization: UPSERT (MERGE/UPDATE) into target_table.

    Логика:
    1. Определение ключевых атрибутов (для JOIN):
       - sql_model.attributes с constraints: ["PRIMARY_KEY"]
       - иначе target_table.primary_keys
    2. Определение полей для UPDATE:
       - все атрибуты sql_model, кроме ключевых
       - фильтр: только те, что есть в target_table
       - ЕСЛИ ПУСТО -> raise UpsertFcError

    Args:
        workflow_new: WorkflowNewModel
        obj_key: Ключ объекта (путь к SQL файлу или имя параметра)
        obj_type: Тип объекта ("sql_object" или "parameter")
        env: MacroEnv с API для рендеринга
    """
    target_table = workflow_new.target_table
    target_table_name = target_table.name if target_table else None

    if not target_table_name:
        raise UpsertFcError(
            f"Target table name is required for upsert_fc. "
            f"Workflow must have target_table defined."
        )

    if obj_type == "sql_object":
        _render_sql_object(workflow_new, obj_key, env, target_table, target_table_name)
    elif obj_type == "parameter":
        _render_parameter(workflow_new, obj_key, env)


def _render_sql_object(
    workflow_new: "WorkflowNewModel",
    obj_key: str,
    env: "BaseMacroEnv",
    target_table,
    target_table_name: str
):
    """Рендеринг для SQL объекта."""
    sql_obj = workflow_new.sql_objects.get(obj_key)
    if not sql_obj:
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
            ctx_config = sql_obj.config.get(context, {})
            sql_tools = ctx_config.get("tools", [])
            if sql_tools and tool not in sql_tools:
                continue

            compiled = env.get_compiled("sql_object", obj_key, context, tool)
            if not compiled:
                continue

            prepared_sql = compiled.get("prepared_sql", "")
            if not prepared_sql:
                continue

            key_attrs = _get_key_attributes(sql_obj, context, target_table, prepared_sql)
            update_attrs = _get_update_attributes(sql_obj, context, target_table, key_attrs, prepared_sql)

            attr_names = []
            if sql_obj.metadata and sql_obj.metadata.aliases:
                attr_names = [a.get('alias', '') for a in sql_obj.metadata.aliases if isinstance(a, dict)]

            if not update_attrs:
                raise UpsertFcError(
                    f"No update columns defined for upsert_fc. "
                    f"Query must have non-key attributes that exist in target table. "
                    f"Key attributes: {key_attrs}, "
                    f"Query attributes: {attr_names}"
                )

            calc_id_literal = "{{CALC_ID}}"

            try:
                rendered = env.render_template(
                    "materialization/upsert_fc_body",
                    tool=tool,
                    target_table=target_table_name,
                    sql=prepared_sql,
                    pk_columns=key_attrs,
                    update_columns=update_attrs,
                    calc_id_literal=calc_id_literal
                )
            except Exception:
                try:
                    rendered = env.render_template(
                        "materialization/upsert_fc_body",
                        tool=None,
                        target_table=target_table_name,
                        sql=prepared_sql,
                        pk_columns=key_attrs,
                        update_columns=update_attrs,
                        calc_id_literal=calc_id_literal
                    )
                except Exception as e:
                    logger.error(f"Failed to render upsert_fc_body: {e}")
                    continue

            env.update_compiled(
                "sql_object", obj_key, context, tool, "rendered_sql", rendered
            )
            env.update_compiled(
                "sql_object", obj_key, context, tool, "target_table", target_table_name
            )


def _render_parameter(
    workflow_new: "WorkflowNewModel",
    obj_key: str,
    env: "BaseMacroEnv"
):
    """Рендеринг для Parameter модели."""
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
            if not prepared_sql:
                continue

            calc_id_literal = "{{CALC_ID}}"

            try:
                rendered = env.render_template(
                    "materialization/upsert_fc_body",
                    tool=tool,
                    target_table=param.name,
                    sql=prepared_sql,
                    pk_columns=[],
                    update_columns=[],
                    calc_id_literal=calc_id_literal
                )
            except Exception:
                try:
                    rendered = env.render_template(
                        "materialization/upsert_fc_body",
                        tool=None,
                        target_table=param.name,
                        sql=prepared_sql,
                        pk_columns=[],
                        update_columns=[],
                        calc_id_literal=calc_id_literal
                    )
                except Exception as e:
                    logger.error(f"Failed to render upsert_fc_body for param: {e}")
                    continue

            env.update_compiled(
                "parameter", obj_key, context, tool, "rendered_sql", rendered
            )
            env.update_compiled(
                "parameter", obj_key, context, tool, "target_table", param.name
            )


def _get_attributes_from_config(sql_obj, context: str) -> List[dict]:
    """Получить атрибуты из config[context]['attributes']"""
    ctx_config = sql_obj.config.get(context, {})
    attrs = ctx_config.get("attributes", [])
    if isinstance(attrs, list):
        return attrs
    return []


def _has_primary_key_constraint(attr: dict) -> bool:
    """Проверить есть ли PRIMARY_KEY в constraints"""
    constraints = attr.get("constraints", {})
    
    if hasattr(constraints, "value"):
        value = constraints.value
    elif isinstance(constraints, dict):
        value = constraints.get("value", [])
    elif isinstance(constraints, list):
        value = constraints
    else:
        value = []
    
    if isinstance(value, str):
        return value == "PRIMARY_KEY"
    return "PRIMARY_KEY" in value


def _get_query_attrs_from_sql(sql_text: str) -> set:
    """Получить атрибуты из SQL текста."""
    if not sql_text:
        return set()
    
    import re
    query_attrs = set()
    
    sql_clean = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
    sql_clean = re.sub(r'--.*?$', '', sql_clean, flags=re.MULTILINE)
    sql_clean = re.sub(r'\{\{[^}]+\}\}', '', sql_clean)
    
    select_match = re.search(r'\bSELECT\s+(.+?)\bFROM\b', sql_clean, re.IGNORECASE | re.DOTALL)
    if select_match:
        cols_text = select_match.group(1)
        
        col_pattern = re.compile(r'(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+as\s+[a-zA-Z_][a-zA-Z0-9_]*)?')
        cols = col_pattern.findall(cols_text)
        
        excluded = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ON', 'AS', 'JOIN', 
                    'LEFT', 'RIGHT', 'INNER', 'OUTER', 'CASE', 'WHEN', 'THEN', 
                    'ELSE', 'END', 'IN', 'NOT', 'NULL', 'TRUE', 'FALSE', 
                    'DISTINCT', 'ALL', 'UNION', 'EXCEPT', 'INTERSECT', 'ORDER',
                    'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'WITH', 'T'}
        query_attrs = {c.lower() for c in cols if c.upper() not in excluded and c}
    
    return query_attrs


def _get_query_attrs(sql_obj, prepared_sql: str) -> set:
    """Получить все атрибуты из запроса (из metadata.aliases или из SQL текста)."""
    query_attrs = set()
    
    if sql_obj.metadata and sql_obj.metadata.aliases:
        query_attrs = {a.get('alias', '').lower() for a in sql_obj.metadata.aliases if isinstance(a, dict)}
    
    if not query_attrs and prepared_sql:
        query_attrs = _get_query_attrs_from_sql(prepared_sql)
    
    if not query_attrs and sql_obj.source_sql:
        query_attrs = _get_query_attrs_from_sql(sql_obj.source_sql)
    
    return query_attrs


def _get_key_attributes(sql_obj, context: str, target_table, prepared_sql: str) -> List[str]:
    """Получить ключевые атрибуты.
    
    Приоритет:
    1. Атрибуты запроса с constraints: ["PRIMARY_KEY"]
    2. Primary keys целевой таблицы, которые ЕСТЬ в запросе
    """
    key_attrs = []
    
    config_attrs = _get_attributes_from_config(sql_obj, context)
    for attr in config_attrs:
        if _has_primary_key_constraint(attr):
            attr_name = attr.get("name", "")
            if attr_name:
                key_attrs.append(attr_name)
    
    if not key_attrs and target_table and target_table.attributes:
        query_attrs = _get_query_attrs(sql_obj, prepared_sql)
        for attr in target_table.attributes:
            if attr.is_primary_key():
                if attr.name.lower() in {q.lower() for q in query_attrs}:
                    key_attrs.append(attr.name)
    
    return key_attrs


def _get_update_attributes(sql_obj, context: str, target_table, key_attrs: List[str], prepared_sql: str) -> List[str]:
    """Получить атрибуты для UPDATE.
    
    Все атрибуты запроса, кроме ключевых.
    Если target_table содержит атрибуты - фильтруем по ним.
    """
    query_attrs = _get_query_attrs(sql_obj, prepared_sql)
    key_attrs_lower = {k.lower() for k in key_attrs}
    
    update_attrs = []
    
    has_target_attrs = target_table and target_table.attributes
    
    for attr_name in query_attrs:
        if attr_name and attr_name.lower() not in key_attrs_lower:
            if has_target_attrs:
                if target_table and target_table.get_attribute(attr_name):
                    target_attr = target_table.get_attribute(attr_name)
                    if target_attr:
                        update_attrs.append(target_attr.name)
            else:
                update_attrs.append(attr_name)
    
    return update_attrs


from FW.logging_config import get_logger

logger = get_logger("materialization_upsert_fc")