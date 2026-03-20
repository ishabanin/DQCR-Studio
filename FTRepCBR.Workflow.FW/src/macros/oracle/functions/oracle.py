"""Tool-specific функции для Oracle.

Переопределяют базовые функции из base.py там, где синтаксис отличается.
"""

from FW.macros import prehook


def nvl2(value, not_null, null):
    """Oracle NVL2."""
    return f"NVL2({value}, {not_null}, {null})"


def decode(*args):
    """Oracle DECODE."""
    if not args or len(args) < 3:
        return str(args[0]) if args else ""
    return f"DECODE({', '.join(str(a) for a in args)})"


def trunc_date(date_val, format_mask='DD'):
    """Oracle TRUNC for dates."""
    return f"TRUNC({date_val}, '{format_mask}')"


def add_months(date_val, months):
    """Oracle ADD_MONTHS."""
    return f"ADD_MONTHS({date_val}, {months})"


def months_between(date1, date2):
    """Oracle MONTHS_BETWEEN."""
    return f"MONTHS_BETWEEN({date1}, {date2})"


def listagg(column, delimiter=',', order_by=None):
    """Oracle LISTAGG."""
    order_by_str = f" ORDER BY {order_by}" if order_by else ""
    return f"LISTAGG({column}, '{delimiter}'){order_by_str} WITHIN GROUP()"


@prehook(output_var="enum_mapping")
def enum2str(p_enum_code):
    """Oracle: Перекодировка enum кода в наименование.
    
    Специфичная реализация для Oracle.
    """
    return f"/* TODO: enum2str Oracle({p_enum_code}) */"
