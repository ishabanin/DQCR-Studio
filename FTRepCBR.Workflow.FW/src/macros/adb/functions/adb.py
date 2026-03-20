"""Tool-specific функции для ADB (ADB Data Warehouse).

Переопределяют базовые функции из base.py там, где синтаксис отличается.
"""

from FW.macros import prehook


def date_trunc(part, value):
    """ADB DATE_TRUNC."""
    return f"DATE_TRUNC('{part}', {value})"


def date_add(part, value, interval):
    """ADB DATE_ADD."""
    return f"DATE_ADD({value}, INTERVAL {interval} {part})"


def date_sub(part, value, interval):
    """ADB DATE_SUB."""
    return f"DATE_SUB({value}, INTERVAL {interval} {part})"


def string_agg(column, delimiter=','):
    """ADB STRING_AGG."""
    return f"STRING_AGG({column}, '{delimiter}')"


@prehook(output_var="enum_mapping")
def enum2str(p_enum_code):
    """ADB: Перекодировка enum кода в наименование.
    
    Специфичная реализация для ADB.
    """
    return f"/* TODO: enum2str ADB({p_enum_code}) */"
