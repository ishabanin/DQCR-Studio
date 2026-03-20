"""Tool-specific функции для PostgreSQL.

Переопределяют базовые функции из base.py там, где синтаксис отличается.
"""

from FW.macros import prehook


def to_timestamp(value, format_mask=None):
    """PostgreSQL TO_TIMESTAMP."""
    if format_mask:
        return f"TO_TIMESTAMP({value}, '{format_mask}')"
    return f"TO_TIMESTAMP({value})"


def age(date1, date2=None):
    """PostgreSQL AGE."""
    if date2:
        return f"AGE({date1}, {date2})"
    return f"AGE({date1})"


def extract(part, value):
    """PostgreSQL EXTRACT."""
    return f"EXTRACT({part} FROM {value})"


def array_agg(column):
    """PostgreSQL ARRAY_AGG."""
    return f"ARRAY_AGG({column})"


def unnest(array):
    """PostgreSQL UNNEST."""
    return f"UNNEST({array})"


def merge_into(target, source, on, matched_update=None, not_matched_insert=None):
    """PostgreSQL MERGE (not directly supported)."""
    return f"/* MERGE not directly supported in PostgreSQL */"


@prehook(output_var="enum_mapping")
def enum2str(p_enum_code):
    """PostgreSQL: Перекодировка enum кода в наименование.
    
    Специфичная реализация для PostgreSQL.
    """
    return f"/* TODO: enum2str PostgreSQL({p_enum_code}) */"


def nvl(value, default):
    """NVL - базовая реализация."""
    return f"COALESCE({value}, {default})"