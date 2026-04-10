"""Materialization: INSERT INTO - workflow_new implementation."""
from typing import TYPE_CHECKING, List

from FW.exceptions.base import BaseFWError
from FW.logging_config import get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv


logger = get_logger("materialization_insert_fc")


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
    workflow_new: "WorkflowNewModel",
    obj_key: str,
    obj_type: str,
    env: "BaseMacroEnv"
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
        workflow_new: WorkflowNewModel
        obj_key: Ключ объекта
        obj_type: Тип объекта ("sql_object" или "parameter")
        env: MacroEnv с API для рендеринга
    """
    target_table = workflow_new.target_table
    target_table_name = target_table.name if target_table else None

    if not target_table_name:
        raise InsertFcError(
            f"Target table name is required for insert_fc. "
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

            key_attrs = _get_key_attributes(sql_obj, target_table)
            query_attrs = _get_query_attributes(sql_obj)

            if not key_attrs:
                raise InsertFcError(
                    f"No key attributes found for insert_fc. "
                    f"Query must have key attributes (constraints: [\"PRIMARY_KEY\"]) that exist in target table. "
                    f"Query attributes: {query_attrs}, "
                    f"Target table primary keys: {target_table.primary_key_names if target_table else []}"
                )

            try:
                target_columns, select_columns = _build_insert_columns(
                    sql_obj, target_table, key_attrs, prepared_sql
                )
            except InsertFcError:
                raise
            except Exception as e:
                raise InsertFcError(f"Error building insert columns: {e}")

            try:
                rendered = env.render_template(
                    "materialization/insert_fc_body",
                    tool=tool,
                    target_table=target_table_name,
                    sql=prepared_sql,
                    target_columns=target_columns,
                    select_columns=select_columns
                )
            except Exception:
                try:
                    rendered = env.render_template(
                        "materialization/insert_fc_body",
                        tool=None,
                        target_table=target_table_name,
                        sql=prepared_sql,
                        target_columns=target_columns,
                        select_columns=select_columns
                    )
                except Exception as e:
                    logger.error(f"Failed to render insert_fc_body: {e}")
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

            try:
                rendered = env.render_template(
                    "materialization/insert_fc_body",
                    tool=tool,
                    target_table=param.name,
                    sql=prepared_sql,
                    target_columns=[],
                    select_columns=[]
                )
            except Exception:
                try:
                    rendered = env.render_template(
                        "materialization/insert_fc_body",
                        tool=None,
                        target_table=param.name,
                        sql=prepared_sql,
                        target_columns=[],
                        select_columns=[]
                    )
                except Exception as e:
                    logger.error(f"Failed to render insert_fc_body for param: {e}")
                    continue

            env.update_compiled(
                "parameter", obj_key, context, tool, "rendered_sql", rendered
            )
            env.update_compiled(
                "parameter", obj_key, context, tool, "target_table", param.name
            )


def _get_key_attributes(sql_obj, target_table) -> List[str]:
    """Получить ключевые атрибуты."""
    key_attrs = []

    if target_table and target_table.attributes:
        for attr in target_table.attributes:
            if attr.is_primary_key():
                key_attrs.append(attr.name)

    return key_attrs


def _get_query_attributes_from_sql(sql_text: str) -> set:
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
    
    return query_attrs


def _get_query_attributes(sql_obj) -> set:
    """Получить атрибуты из запроса."""
    query_attrs = set()

    if sql_obj.metadata and sql_obj.metadata.aliases:
        query_attrs = {a.get('alias', '').lower() for a in sql_obj.metadata.aliases if isinstance(a, dict)}

    return query_attrs


def _build_insert_columns(sql_obj, target_table, key_attrs: List[str], prepared_sql: str = "") -> tuple:
    """Построить списки колонок для INSERT.

    Логика target_columns:
    1. Ключевой (is_key=True) - добавляется всегда
    2. Обязательный (required=True) - добавляется всегда, если нет в запросе - подставляется default_value
    3. Присутствует в запросе - добавляется если есть в запросе

    Returns:
        (target_columns, select_columns)
    """
    query_attrs = _get_query_attributes(sql_obj)
    
    if not query_attrs:
        if prepared_sql and len(prepared_sql) > 10:
            query_attrs = _get_query_attributes_from_sql(prepared_sql)
        if not query_attrs and sql_obj.source_sql and len(sql_obj.source_sql) > 10:
            query_attrs = _get_query_attributes_from_sql(sql_obj.source_sql)
    

    
    target_columns = []
    select_columns = []

    if target_table and target_table.attributes:
        for attr in target_table.attributes:
            is_key = attr.is_primary_key()
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