"""Базовые функции для Jinja2.

Эти функции являются базовыми реализациями и могут быть переопределены
в tool-specific файлах (oracle.py, adb.py, postgresql.py).

Структура:
- main/functions/base.py - полный набор базовых функций
- oracle/functions/oracle.py - переопределения для Oracle
- adb/functions/adb.py - переопределения для ADB
- postgresql/functions/postgresql.py - переопределения для PostgreSQL
"""

from FW.macros import prehook


def star(source, except_cols=None, alias=None):
    """dbt-utils star().
    
    Generates SELECT * with optional exclusion and prefix.
    """
    if except_cols is None:
        except_cols = []
    
    table_ref = f"{source}.*" if alias else "*"
    
    if except_cols:
        return f"/* TODO: star() with exclusions not fully implemented */ {table_ref}"
    
    return table_ref


def get_relations_by_prefix(schema: str, prefix: str):
    """dbt-utils get_relations_by_prefix() equivalent."""
    return []


def pivot(columns, values):
    """dbt-utils pivot() equivalent."""
    return []


def unpivot(columns, names):
    """dbt-utils unpivot() equivalent."""
    return []


def get_column_names(ref):
    """Get column names from a reference."""
    return []


def get_table_columns(ref):
    """Get columns from table."""
    return []


def current_timestamp():
    """CURRENT_TIMESTAMP - базовая реализация."""
    return "CURRENT_TIMESTAMP"


def current_date():
    """CURRENT_DATE - базовая реализация."""
    return "CURRENT_DATE"


def now():
    """NOW() - базовая реализация."""
    return "NOW()"


def sysdate():
    """SYSDATE - базовая реализация (fallback)."""
    return "SYSDATE"


def to_char(value, format_mask=None):
    """TO_CHAR - базовая реализация."""
    if format_mask:
        return f"TO_CHAR({value}, '{format_mask}')"
    return f"TO_CHAR({value})"


def to_date(value, format_mask=None):
    """TO_DATE - базовая реализация."""
    if format_mask:
        return f"TO_DATE({value}, '{format_mask}')"
    return f"TO_DATE({value})"


def to_timestamp(value, format_mask=None):
    """TO_TIMESTAMP - базовая реализация."""
    if format_mask:
        return f"TO_TIMESTAMP({value}, '{format_mask}')"
    return f"TO_TIMESTAMP({value})"


def coalesce(*args):
    """COALESCE - базовая реализация."""
    return f"COALESCE({', '.join(str(a) for a in args)})"


def nvl(value, default):
    """NVL - базовая реализация."""
    return f"NVL({value}, {default})"


def nvl2(value, not_null, null):
    """NVL2 - базовая реализация."""
    return f"NVL2({value}, {not_null}, {null})"


def nullif(val1, val2):
    """NULLIF - базовая реализация."""
    return f"NULLIF({val1}, {val2})"


def greatest(*args):
    """GREATEST - базовая реализация."""
    return f"GREATEST({', '.join(str(a) for a in args)})"


def least(*args):
    """LEAST - базовая реализация."""
    return f"LEAST({', '.join(str(a) for a in args)})"


def decode(*args):
    """DECODE - базовая реализация."""
    if not args or len(args) < 3:
        return str(args[0]) if args else ""
    return f"DECODE({', '.join(str(a) for a in args)})"


def trunc_date(date_val, format_mask='DD'):
    """TRUNC for dates - базовая реализация."""
    return f"TRUNC({date_val}, '{format_mask}')"


def add_months(date_val, months):
    """ADD_MONTHS - базовая реализация."""
    return f"ADD_MONTHS({date_val}, {months})"


def months_between(date1, date2):
    """MONTHS_BETWEEN - базовая реализация."""
    return f"MONTHS_BETWEEN({date1}, {date2})"


def date_trunc(part, value):
    """DATE_TRUNC - базовая реализация."""
    return f"DATE_TRUNC('{part}', {value})"


def date_add(part, value, interval):
    """DATE_ADD - базовая реализация."""
    return f"DATE_ADD({value}, INTERVAL {interval} {part})"


def date_sub(part, value, interval):
    """DATE_SUB - базовая реализация."""
    return f"DATE_SUB({value}, INTERVAL {interval} {part})"


def age(date1, date2=None):
    """AGE - базовая реализация."""
    if date2:
        return f"AGE({date1}, {date2})"
    return f"AGE({date1})"


def extract(part, value):
    """EXTRACT - базовая реализация."""
    return f"EXTRACT({part} FROM {value})"


def row_number():
    """ROW_NUMBER() OVER() - базовая реализация."""
    return "ROW_NUMBER() OVER()"


def rank():
    """RANK() OVER() - базовая реализация."""
    return "RANK() OVER()"


def dense_rank():
    """DENSE_RANK() OVER() - базовая реализация."""
    return "DENSE_RANK() OVER()"


def lead(column, offset=1, default=None):
    """LEAD - базовая реализация."""
    default_str = f", {default}" if default else ""
    return f"LEAD({column}, {offset}{default_str}) OVER()"


def lag(column, offset=1, default=None):
    """LAG - базовая реализация."""
    default_str = f", {default}" if default else ""
    return f"LAG({column}, {offset}{default_str}) OVER()"


def listagg(column, delimiter=',', order_by=None):
    """LISTAGG - базовая реализация."""
    order_by_str = f" ORDER BY {order_by}" if order_by else ""
    return f"LISTAGG({column}, '{delimiter}'){order_by_str} WITHIN GROUP()"


def string_agg(column, delimiter=','):
    """STRING_AGG - базовая реализация."""
    return f"STRING_AGG({column}, '{delimiter}')"


def array_agg(column):
    """ARRAY_AGG - базовая реализация."""
    return f"ARRAY_AGG({column})"


def unnest(array):
    """UNNEST - базовая реализация."""
    return f"UNNEST({array})"


def merge_into(target, source, on, matched_update=None, not_matched_insert=None):
    """MERGE INTO - базовая реализация (placeholder)."""
    return f"MERGE INTO {target} USING {source} ON ({on})"


@prehook(output_var="enum_mapping")
def enum2str(p_enum_code):
    """Перекодировка enum кода в наименование.
    
    Генерирует CASE выражение для перекодировки числового кода
    в строковое наименование.
    
    Пример результата:
        CASE p_enum_code
            WHEN 1 THEN 'A'
            WHEN 2 THEN 'B'
            ...
        END
    
    Примечание: Реализация будет добавлена позже.
    При вызове вернет placeholder строку.
    """
    return f"/* TODO: enum2str({p_enum_code}) - требует реализации */"
