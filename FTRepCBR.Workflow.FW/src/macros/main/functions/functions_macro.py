"""Function macro application logic.

Применяет функции из macros/functions к SQL объектам и параметрам.
Для каждой функции в SQL находится соответствующий макрос и применяется к prepared_sql.

Пример:
    SQL: SELECT TO_CHAR(col1, 'YYYY-MM-DD') FROM table1
    Macro: to_char(value, format_mask=None, workflow, env, obj_type, obj_key)
    Result: SELECT TO_CHAR(col1, 'YYYY-MM-DD') FROM table1 ( transformed )

Работает с WorkflowNewModel через MacroEnv.
"""

import re
from typing import Optional, TYPE_CHECKING, List, Dict, Any, Callable

from FW.logging_config import get_logger as _get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv
    from FW.models.sql_object import SQLObjectModel
    from FW.models.parameter import ParameterModel

logger = _get_logger("functions_macro")


FUNCTION_CALL_PATTERN = re.compile(
    r"\b([A-Z_][A-Z0-9_]*)\s*\((.*)\)", re.IGNORECASE | re.DOTALL
)

SQL_KEYWORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "AND",
    "OR",
    "NOT",
    "IN",
    "IS",
    "NULL",
    "TRUE",
    "FALSE",
    "AS",
    "ON",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "FULL",
    "CROSS",
    "UNION",
    "INTERSECT",
    "EXCEPT",
    "ORDER",
    "BY",
    "GROUP",
    "HAVING",
    "LIMIT",
    "OFFSET",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "INSERT",
    "INTO",
    "VALUES",
    "UPDATE",
    "SET",
    "DELETE",
    "CREATE",
    "DROP",
    "ALTER",
    "TABLE",
    "INDEX",
    "VIEW",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "CAST",
    "EXTRACT",
    "OVER",
    "PARTITION",
    "WINDOW",
    "ROWS",
    "RANGE",
    "PRECEDING",
    "FOLLOWING",
    "CURRENT",
    "UNBOUNDED",
    "NULLS",
    "FIRST",
    "LAST",
}


def find_all_function_calls(
    sql_content: str, skip_ranges: List[tuple] = None
) -> List[Dict[str, Any]]:
    """Find all function calls in SQL with their positions.

    Args:
        sql_content: SQL content to search
        skip_ranges: List of (start, end) ranges to skip (already processed functions)

    Returns:
        List of dicts with 'name', 'start', 'end', 'full_call'
    """
    if skip_ranges is None:
        skip_ranges = []
    functions = []

    func_name_pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

    comment_blocks = []
    for m in re.finditer(r"/\*.*?\*/", sql_content, re.DOTALL):
        comment_blocks.append((m.start(), m.end()))
    for m in re.finditer(r"--.*?$", sql_content, re.MULTILINE):
        comment_blocks.append((m.start(), m.end()))

    for match in func_name_pattern.finditer(sql_content):
        func_pos = match.start()

        is_in_comment = any(start <= func_pos < end for start, end in comment_blocks)
        if is_in_comment:
            continue

        is_in_skip = any(start <= func_pos < end for start, end in skip_ranges)
        if is_in_skip:
            continue

        func_name = match.group(1).upper()
        if func_name in SQL_KEYWORDS or func_name.isdigit():
            continue

        start_paren = match.end() - 1
        end_paren = _find_closing_paren(sql_content, start_paren)
        if end_paren == -1:
            continue

        full_call = sql_content[start_paren : end_paren + 1]
        functions.append(
            {
                "name": func_name,
                "start": func_pos,
                "end": end_paren + 1,
                "full_call": full_call,
            }
        )

    functions.sort(key=lambda x: x["start"])
    return functions


def _find_closing_paren(sql_content: str, start_paren: int) -> int:
    """Find position of closing parenthesis matching opening at start_paren.

    Args:
        sql_content: SQL content
        start_paren: Position of opening parenthesis

    Returns:
        Position of closing parenthesis, or -1 if not found
    """
    if start_paren >= len(sql_content) or sql_content[start_paren] != "(":
        return -1

    depth = 0
    i = start_paren
    in_string = False
    string_char = None

    while i < len(sql_content):
        char = sql_content[i]

        if char in ("'", '"') and not in_string:
            in_string = True
            string_char = char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
        elif not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return i

        i += 1

    return -1


def split_sql_by_functions(
    sql_content: str, function_calls: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Split SQL into chunks: text and function chunks.

    Filters to only include top-level functions (not nested inside other functions).

    Args:
        sql_content: SQL content
        function_calls: List of function calls from find_all_function_calls

    Returns:
        List of chunks with 'type' ('text' or 'function'), 'content', optional 'name'
    """
    top_level_funcs = _filter_top_level_functions(function_calls)

    chunks = []
    last_pos = 0

    for func in top_level_funcs:
        func_start = func["start"]
        func_end = func["end"]

        if func_start > last_pos:
            chunks.append({"type": "text", "content": sql_content[last_pos:func_start]})

        chunks.append(
            {
                "type": "function",
                "name": func["name"],
                "content": sql_content[func_start:func_end],
            }
        )

        last_pos = func_end

    if last_pos < len(sql_content):
        chunks.append({"type": "text", "content": sql_content[last_pos:]})

    return chunks


def _filter_top_level_functions(
    function_calls: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Filter to only top-level functions (not nested inside other functions).

    Args:
        function_calls: List of function dicts with 'start' and 'end'

    Returns:
        List of only top-level functions
    """
    if not function_calls:
        return []

    top_level = [function_calls[0]]

    for i in range(1, len(function_calls)):
        current = function_calls[i]
        prev = top_level[-1]

        if current["start"] >= prev["end"]:
            top_level.append(current)

    return top_level


def process_function_arguments_recursive(
    args_str: str,
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str,
    obj_key: str,
    max_depth: int = 10,
) -> str:
    """Recursively process function arguments, replacing nested functions.

    Args:
        args_str: Arguments string (e.g., "nullif(t.col,'N/D'), '<empty>'")
        tool: Target tool
        context: Context name
        workflow_new: WorkflowNewModel
        env: Macro environment
        obj_type: Object type
        obj_key: Object key
        max_depth: Maximum recursion depth

    Returns:
        Processed arguments string
    """
    if max_depth <= 0:
        return args_str

    function_calls = find_all_function_calls(args_str)

    if not function_calls:
        return args_str

    chunks = split_sql_by_functions(args_str, function_calls)

    result_parts = []
    for chunk in chunks:
        if chunk["type"] == "text":
            result_parts.append(chunk["content"])
        else:
            processed = process_function_chunk(
                chunk,
                tool,
                context,
                workflow_new,
                env,
                obj_type,
                obj_key,
                max_depth - 1,
            )
            result_parts.append(processed)

    return "".join(result_parts)


def process_function_chunk(
    chunk: Dict[str, Any],
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str,
    obj_key: str,
    max_depth: int = 10,
) -> str:
    """Process a function chunk recursively.

    Args:
        chunk: Chunk dict with 'type' and 'content'
        tool: Target tool (oracle, adb, postgresql)
        context: Context name
        workflow_new: WorkflowNewModel
        env: Macro environment
        obj_type: Object type
        obj_key: Object key
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Processed content
    """
    if chunk["type"] == "text":
        return chunk["content"]

    if chunk["type"] != "function":
        return chunk.get("content", "")

    func_name = chunk["name"]
    func_content = chunk["content"]

    open_paren = func_content.find("(")
    close_paren = func_content.rfind(")")

    if open_paren < 0 or close_paren < 0 or not func_content.endswith(")"):
        return func_content

    args_str = func_content[open_paren + 1 : close_paren]

    processed_args = process_function_arguments_recursive(
        args_str, tool, context, workflow_new, env, obj_type, obj_key, max_depth - 1
    )

    func_call = processed_args

    result = apply_function_macro(
        func_name,
        func_call,
        tool,
        context,
        workflow_new,
        env,
        obj_type,
        obj_key,
    )

    if result == func_call:
        return func_content

    return result


def process_arguments_recursive(
    args_str: str,
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str,
    obj_key: str,
    max_depth: int = 10,
) -> str:
    """Recursively process function arguments, replacing nested functions.

    Args:
        args_str: Arguments string (e.g., "nullif(t.col,'N/D'), '<empty>'")
        tool: Target tool
        context: Context name
        workflow_new: WorkflowNewModel
        env: Macro environment
        obj_type: Object type
        obj_key: Object key
        max_depth: Maximum recursion depth

    Returns:
        Processed arguments string
    """
    if max_depth <= 0:
        return args_str

    function_calls = find_all_function_calls(args_str)

    if not function_calls:
        return args_str

    chunks = split_sql_by_functions(args_str, function_calls)

    result_parts = []
    for chunk in chunks:
        if chunk["type"] == "text":
            result_parts.append(chunk["content"])
        else:
            processed = process_function_chunk(
                chunk,
                tool,
                context,
                workflow_new,
                env,
                obj_type,
                obj_key,
                max_depth - 1,
            )
            result_parts.append(processed)

    return "".join(result_parts)


def apply_function_macro(
    func_name: str,
    func_call: str,
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str,
    obj_key: str,
) -> str:
    """Применить function macro к вызову функции.

    Args:
        func_name: Имя функции (напр. TO_CHAR)
        func_call: Полный вызов функции (напр. "TO_CHAR(col1, 'YYYY-MM-DD')")
        tool: Целевой tool (oracle, adb, postgresql)
        context: Имя контекста
        workflow_new: WorkflowNewModel
        env: Окружение макроса
        obj_type: Тип объекта ("sql_object" или "parameter")
        obj_key: Ключ объекта

    Returns:
        Преобразованный вызов функции
    """
    from FW.macros import get_macro_registry

    registry = get_macro_registry()

    func_name_lower = func_name.lower()

    try:
        func_macro = registry.get_function_macro(func_name_lower, tool)
    except Exception as e:
        logger.debug(
            f"Function macro '{func_name_lower}' not found for tool '{tool}': {e}"
        )
        return func_call

    try:
        args = _parse_function_args(func_call)

        import inspect

        sig = inspect.signature(func_macro)
        kwargs = {
            "workflow": workflow_new,
            "env": env,
            "obj_type": obj_type,
            "obj_key": obj_key,
        }

        filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

        result = func_macro(*args, **filtered_kwargs)

        return str(result) if result is not None else func_call

    except Exception as e:
        logger.warning(f"Error applying function macro '{func_name}': {e}")
        return func_call


def _parse_function_args(func_call: str) -> List[str]:
    """Parse function arguments from function call string.

    Args:
        func_call: String like "col1, 'YYYY-MM-DD'" or "col1"

    Returns:
        List of arguments
    """
    args = []
    current_arg = ""
    paren_depth = 0
    in_string = False
    string_char = None

    for char in func_call:
        if char in ("'", '"') and not in_string:
            in_string = True
            string_char = char
            current_arg += char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
            current_arg += char
        elif char == "(" and not in_string:
            paren_depth += 1
            current_arg += char
        elif char == ")" and not in_string:
            paren_depth -= 1
            current_arg += char
        elif char == "," and paren_depth == 0 and not in_string:
            args.append(current_arg.strip())
            current_arg = ""
        else:
            current_arg += char

    if current_arg.strip():
        args.append(current_arg.strip())

    return args


def apply_all_functions_to_object(
    sql_obj: "SQLObjectModel",
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str = "sql_object",
    obj_key: str = None,
) -> str:
    """Применить все function macros к SQL объекту.

    Использует подход с разделением на куски для избежания цепных замен.
    Каждая функция обрабатывается один раз, вложенные функции обрабатываются рекурсивно.

    Args:
        sql_obj: SQL объект
        tool: Целевой tool
        context: Имя контекста
        workflow_new: WorkflowNewModel
        env: Окружение макроса
        obj_type: Тип объекта
        obj_key: Ключ объекта

    Returns:
        Преобразованный prepared_sql
    """
    current_compiled = env.get_compiled(obj_type, obj_key, context, tool)
    if not current_compiled:
        return ""

    prepared_sql = current_compiled.get("prepared_sql", "")
    if not prepared_sql:
        return prepared_sql

    function_calls = find_all_function_calls(prepared_sql)

    if not function_calls:
        return prepared_sql

    chunks = split_sql_by_functions(prepared_sql, function_calls)

    result_parts = []
    for chunk in chunks:
        processed = process_function_chunk(
            chunk, tool, context, workflow_new, env, obj_type, obj_key
        )
        result_parts.append(processed)

    return "".join(result_parts)


def apply_all_functions_to_parameter(
    param_obj: "ParameterModel",
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv",
    obj_type: str = "parameter",
    obj_key: str = None,
) -> str:
    """Применить все function macros к параметру.

    Использует тот же подход что и для SQL объектов - разделение на куски
    для корректной обработки вложенных функций.

    Args:
        param_obj: Параметр
        tool: Целевой tool
        context: Имя контекста
        workflow_new: WorkflowNewModel
        env: Окружение макроса
        obj_type: Тип объекта
        obj_key: Ключ объекта

    Returns:
        Преобразованный prepared_sql
    """
    current_compiled = env.get_compiled(obj_type, obj_key, context, tool)
    if not current_compiled:
        return ""

    prepared_sql = current_compiled.get("prepared_sql", "")
    if not prepared_sql:
        return prepared_sql

    function_calls = find_all_function_calls(prepared_sql)

    if not function_calls:
        return prepared_sql

    chunks = split_sql_by_functions(prepared_sql, function_calls)

    result_parts = []
    for chunk in chunks:
        processed = process_function_chunk(
            chunk, tool, context, workflow_new, env, obj_type, obj_key
        )
        result_parts.append(processed)

    return "".join(result_parts)
