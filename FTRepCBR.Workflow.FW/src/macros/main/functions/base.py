"""Базовые функции для Jinja2.

Эти функции являются базовыми реализациями и могут быть переопределены
в tool-specific файлах (oracle.py, adb.py, postgresql.py).

Структура:
- main/functions/base.py - полный набор базовых функций
- oracle/functions/oracle.py - переопределения для Oracle
- adb/functions/adb.py - переопределения для ADB
- postgresql/functions/postgresql.py - переопределения для PostgreSQL

Каждая функция имеет последними параметрами:
- workflow: WorkflowNewModel - модель workflow
- obj_type: str - тип объекта ("sql_object" или "parameter")
- obj_key: str - ключ объекта
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv


def star(
    source,
    except_cols=None,
    alias=None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """dbt-utils star().

    Generates SELECT * with optional exclusion and prefix.
    """
    if except_cols is None:
        except_cols = []

    table_ref = f"{source}.*" if alias else "*"

    if except_cols:
        return f"/* TODO: star() with exclusions not fully implemented */ {table_ref}"

    return table_ref


def get_relations_by_prefix(
    schema: str,
    prefix: str,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """dbt-utils get_relations_by_prefix() equivalent."""
    return []


def pivot(
    columns,
    values,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """dbt-utils pivot() equivalent."""
    return []


def unpivot(
    columns,
    names,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """dbt-utils unpivot() equivalent."""
    return []


def get_column_names(
    ref,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """Get column names from a reference."""
    return []


def get_table_columns(
    ref,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """Get columns from table."""
    return []


def current_timestamp(
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """CURRENT_TIMESTAMP - базовая реализация."""
    return "CURRENT_TIMESTAMP"


def current_date(
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """CURRENT_DATE - базовая реализация."""
    return "CURRENT_DATE"


def now(
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """NOW() - базовая реализация."""
    return "NOW()"


def sysdate(
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """SYSDATE - базовая реализация (fallback)."""
    return "SYSDATE"


def to_char(
    value,
    format_mask=None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """TO_CHAR - базовая реализация."""
    if format_mask:
        return f"TO_CHAR({value}, '{format_mask}')"
    return f"TO_CHAR({value})"


def to_date(
    value,
    format_mask=None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """TO_DATE - базовая реализация."""
    if format_mask:
        return f"TO_DATE({value}, '{format_mask}')"
    return f"TO_DATE({value})"


def to_timestamp(
    value,
    format_mask=None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """TO_TIMESTAMP - базовая реализация."""
    if format_mask:
        return f"TO_TIMESTAMP({value}, '{format_mask}')"
    return f"TO_TIMESTAMP({value})"


def coalesce(
    *args,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """COALESCE - базовая реализация."""
    args_list = list(args)
    sql_args = args_list[:-4] if len(args_list) > 4 else args_list
    return f"COALESCE({', '.join(str(a) for a in sql_args)})"


def nvl(
    value,
    default,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """NVL - базовая реализация."""
    return f"NVL({value}, {default})"


def nvl2(
    value,
    not_null,
    null,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """NVL2 - базовая реализация."""
    return f"NVL2({value}, {not_null}, {null})"


def nullif(
    val1,
    val2,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """NULLIF - базовая реализация."""
    return f"NULLIF({val1}, {val2})"


def greatest(
    *args,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """GREATEST - базовая реализация."""
    args_list = list(args)
    sql_args = args_list[:-4] if len(args_list) > 4 else args_list
    return f"GREATEST({', '.join(str(a) for a in sql_args)})"


def least(
    *args,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """LEAST - базовая реализация."""
    args_list = list(args)
    sql_args = args_list[:-4] if len(args_list) > 4 else args_list
    return f"LEAST({', '.join(str(a) for a in sql_args)})"


def decode(
    *args,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """DECODE - базовая реализация."""
    args_list = list(args)
    sql_args = args_list[:-4] if len(args_list) > 4 else args_list
    if not sql_args or len(sql_args) < 3:
        return str(sql_args[0]) if sql_args else ""
    return f"DECODE({', '.join(str(a) for a in sql_args)})"


def trunc_date(
    date_val,
    format_mask="DD",
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """TRUNC for dates - базовая реализация."""
    return f"TRUNC({date_val}, '{format_mask}')"


def add_months(
    date_val,
    months,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """ADD_MONTHS - базовая реализация."""
    return f"ADD_MONTHS({date_val}, {months})"


def months_between(
    date1,
    date2,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """MONTHS_BETWEEN - базовая реализация."""
    return f"MONTHS_BETWEEN({date1}, {date2})"


def date_trunc(
    part,
    value,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """DATE_TRUNC - базовая реализация."""
    return f"DATE_TRUNC('{part}', {value})"


def date_add(
    part,
    value,
    interval,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """DATE_ADD - базовая реализация."""
    return f"DATE_ADD({value}, INTERVAL {interval} {part})"


def date_sub(
    part,
    value,
    interval,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """DATE_SUB - базовая реализация."""
    return f"DATE_SUB({value}, INTERVAL {interval} {part})"


def age(
    date1,
    date2=None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """AGE - базовая реализация."""
    if date2:
        return f"AGE({date1}, {date2})"
    return f"AGE({date1})"


def extract(
    part,
    value,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """EXTRACT - базовая реализация."""
    return f"EXTRACT({part} FROM {value})"

def unnest(
    array,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """UNNEST - базовая реализация."""
    return f"UNNEST({array})"


def merge_into(
    target,
    source,
    on,
    matched_update=None,
    not_matched_insert=None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """MERGE INTO - базовая реализация (placeholder)."""
    return f"MERGE INTO {target} USING {source} ON ({on})"


def wf_get_enum_by_refrcode(
    p_expr,
    p_refr_code,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
):
    """Перекодировка enum кода в наименование.

    Генерирует CASE выражение для перекодировки числового кода
    в строковое наименование.

    Пример результата:
        CASE p_enum_code
            WHEN 1 THEN 'A'
            WHEN 2 THEN 'B'
            ...
        END

    Примечание: Базовая реализация возвращает placeholder строку.
    """

    from FW.models.parameter import ParameterModel, ParameterValue
    from FW.models.workflow_new import WorkflowNewModel

    workflow: WorkflowNewModel = workflow
    param_key = f"GET_ENUM_{p_refr_code.replace("'", '')}"
    if not param_key in workflow.parameters:
        value = f"""
             select s.str1,
                    s.str2
               from (
                     select rr.numcode,
                            'when ' || rr.NumCode || ' then ''' || rr.RefrCode || ''' ' as str1,
                            'when ''' || rr.RefrCode || ''' then ''' || rr.Brief || ''' ' as str2
                       from DWR_tReference r
                             left join DWR_tReferenceRec rr
                                    on rr.ReferenceID = r.ID
                      where r.Code = {p_refr_code}
                    ) s
              order by s.NumCode
"""
        param = ParameterModel(
            name=param_key,
            domain_type="record",
            description=f"Получение значений для перечислимого типа {p_refr_code}",
            attributes=[],
            values={"all": ParameterValue(type="dynamic", value=value)},
            generated=True,
        )

        param.attributes.append(
            {
                "name": "NTC_" + p_refr_code.replace("'", ""),
                "domain_type": "sql.expression.when.list",
            }
        )

        param.attributes.append(
            {
                "name": "RTC_" + p_refr_code.replace("'", ""),
                "domain_type": "sql.expression.when.list",
            }
        )

        env.add_parameter(param)

        source_obj = None
        if obj_type == "sql_object" and obj_key:
            source_obj = workflow.sql_objects.get(obj_key)
        elif obj_type == "parameter" and obj_key:
            source_obj = workflow.parameters.get(obj_key)

        for ctx in workflow.contexts.keys():
            if source_obj and ctx in source_obj.config:
                ctx_config = source_obj.config[ctx]
                ctx_tools = ctx_config.get("tools", []) if ctx_config else []
            else:
                ctx_obj = workflow.contexts.get(ctx)
                ctx_tools = (
                    ctx_obj.tools if ctx_obj and ctx_obj.tools else workflow.tools
                )

            param.config[ctx] = {"tools": ctx_tools}

            for t in ctx_tools:
                if not env.has_step_in_graph(param_key, ctx, t):
                    env.add_step_to_graph("parameter", param_key, ctx, t, "param")

            for t in ctx_tools:
                env.update_compiled(
                    "parameter",
                    param_key,
                    ctx,
                    t,
                    "prepared_sql",
                    param.values.get("all", "").value
                    if param.values.get("all")
                    else "",
                )
                env.update_compiled("parameter", param_key, ctx, t, "model_refs", {})

    return f"case {p_expr} {{{{RTC_{p_refr_code.replace("'", '')}}}}} end"


def fw_render_props(
    prop_name: str,
    value: Any = None,
    domain_type: str = None,
    workflow: "Optional[Any]" = None,
    env: "Optional[Any]" = None,
    obj_type: "Optional[str]" = None,
    obj_key: "Optional[str]" = None,
) -> str:
    """Подстановка значений свойств, флагов, констант в SQL.

    Используется для подмены ссылок вида:
    - _p.props.<property> -> значение свойства проекта
    - _ctx.flags.<flag> -> значение флага контекста
    - _ctx.flags.<flag>.<subflag> -> значение вложенного флага
    - _ctx.const.<constant> -> значение константы контекста

    Args:
        prop_name: имя свойства/флага/константы
        value: значение (обычно не используется, получается из workflow)
        domain_type: доменный тип для форматирования
        workflow: WorkflowNewModel
        env: Macro environment
        obj_type: тип объекта ("sql_object" или "parameter")
        obj_key: ключ объекта

    Returns:
        Подставленное значение в виде строки
    """
    if not workflow:
        return str(value) if value is not None else ""

    context = getattr(env, "_context_name", None) or "default"
    result = None
    ref_type = None

    if prop_name.startswith("props."):
        actual_prop = prop_name[6:]
        ref_type = "project_prop"
        if workflow.project and workflow.project.project_properties:
            prop_info = workflow.project.project_properties.get(actual_prop)
            if isinstance(prop_info, dict):
                result = prop_info.get("value")
            elif prop_info is not None:
                result = prop_info
        if result is None:
            result = value

    elif prop_name.startswith("flags."):
        actual_flag = prop_name[6:]
        ref_type = "context_flag"
        context_obj = workflow.contexts.get(context)
        if context_obj:
            result = context_obj.flags.get(actual_flag)
        if result is None:
            result = value

    elif prop_name.startswith("const."):
        actual_const = prop_name[6:]
        ref_type = "context_const"
        context_obj = workflow.contexts.get(context)
        if context_obj:
            result = context_obj.constants.get(actual_const)
        if result is None:
            result = value

    else:
        result = value

    if result is None:
        result = value

    if domain_type == "string" and result is not None:
        return f"'{result}'"
    elif domain_type == "number":
        return str(result)
    elif domain_type == "boolean":
        return "TRUE" if result else "FALSE"
    else:
        return str(result) if result is not None else ""
