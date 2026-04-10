"""Обработка материализации CTE в workflow_new.

Создает SQL объекты для CTE с материализацией, отличной от ephemeral.
Обновляет prepared_sql родительских объектов, заменяя ссылки на материализованные CTE.
"""

import re
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass

from FW.logging_config import get_logger
from FW.models.sql_object import SQLObjectModel, ConfigValue
from FW.parsing.sql_metadata import SQLMetadataParser, SQLMetadata


logger = get_logger("cte_materialization")

def get_main_sql(sql_text):
    """
    Возвращает основной SELECT (первый SELECT в самой верхней области, не внутри CTE)
    Возвращает: (text, start_pos, end_pos) или (None, -1, -1)
    """
    i = 0
    length = len(sql_text)
    paren_depth = 0
    in_single_quote = False
    in_double_quote = False
    after_with = False  # Флаг, что мы находимся после WITH
    
    while i < length:
        # Пропускаем комментарии
        if i + 1 < length and sql_text[i:i+2] == '--':
            # Однострочный комментарий
            while i < length and sql_text[i] != '\n':
                i += 1
            continue
        elif i + 1 < length and sql_text[i:i+2] == '/*':
            # Многострочный комментарий
            i += 2
            while i + 1 < length and sql_text[i:i+2] != '*/':
                i += 1
            i += 2
            continue
        
        # Обработка кавычек (пропускаем строковые литералы)
        if sql_text[i] == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            i += 1
            continue
        elif sql_text[i] == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            i += 1
            continue
        
        # Пропускаем содержимое внутри кавычек
        if in_single_quote or in_double_quote:
            i += 1
            continue
        
        # Отслеживаем скобки
        if sql_text[i] == '(':
            paren_depth += 1
            after_with = False  # Сбрасываем флаг при входе в скобки
        elif sql_text[i] == ')':
            paren_depth -= 1
        
        # Ищем WITH на глубине 0
        if paren_depth == 0 and i + 3 < length and not after_with:
            if sql_text[i:i+4].upper() == 'WITH' and (i == 0 or not sql_text[i-1].isalnum()):
                after_with = True
                i += 4
                continue
        
        # Ищем SELECT на глубине 0, но не после WITH
        if paren_depth == 0 and not after_with and i + 5 < length:
            # Проверяем слово SELECT (регистронезависимо)
            if sql_text[i:i+6].upper() == 'SELECT':
                # Проверяем, что это не часть другого слова
                if i == 0 or not (sql_text[i-1].isalnum() or sql_text[i-1] == '_'):
                    next_char = sql_text[i+6] if i+6 < length else ''
                    if not (next_char.isalnum() or next_char == '_'):
                        # Нашли начало основного SELECT
                        start_pos = i
                        
                        # Ищем конец запроса
                        end_pos = length
                        semicolon_pos = sql_text.find(';', start_pos)
                        if semicolon_pos != -1:
                            end_pos = semicolon_pos
                        
                        return (sql_text[start_pos:end_pos].strip(), start_pos, end_pos)
        
        i += 1
    
    return (None, -1, -1)


def get_with_by_name(sql_text, cte_name):
    """
    Возвращает CTE запрос по имени
    Возвращает: (text, start_pos, end_pos) или (None, -1, -1)
    text включает: "alias AS (запрос),"
    """
    i = 0
    length = len(sql_text)
    paren_depth = 0
    in_single_quote = False
    in_double_quote = False
    
    # Ищем начало WITH
    with_pos = -1
    while i < length:
        # Пропускаем комментарии
        if i + 1 < length and sql_text[i:i+2] == '--':
            while i < length and sql_text[i] != '\n':
                i += 1
            continue
        elif i + 1 < length and sql_text[i:i+2] == '/*':
            i += 2
            while i + 1 < length and sql_text[i:i+2] != '*/':
                i += 1
            i += 2
            continue
        
        # Обработка кавычек
        if sql_text[i] == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            i += 1
            continue
        elif sql_text[i] == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            i += 1
            continue
        
        if in_single_quote or in_double_quote:
            i += 1
            continue
        
        # Ищем WITH на глубине 0
        if paren_depth == 0 and i + 3 < length:
            if sql_text[i:i+4].upper() == 'WITH' and (i == 0 or not sql_text[i-1].isalnum()):
                with_pos = i + 4  # Позиция после WITH
                break
        
        i += 1
    
    if with_pos == -1:
        return (None, -1, -1)
    
    # Теперь ищем нужный CTE после WITH
    i = with_pos
    while i < length:
        # Пропускаем пробелы и переводы строк
        while i < length and sql_text[i].isspace():
            i += 1
        
        if i >= length:
            break
        
        # Пропускаем комментарии
        if i + 1 < length and sql_text[i:i+2] == '--':
            while i < length and sql_text[i] != '\n':
                i += 1
            continue
        elif i + 1 < length and sql_text[i:i+2] == '/*':
            i += 2
            while i + 1 < length and sql_text[i:i+2] != '*/':
                i += 1
            i += 2
            continue
        
        # Находим начало имени CTE
        name_start = i
        while i < length and (sql_text[i].isalnum() or sql_text[i] == '_'):
            i += 1
        
        if name_start == i:
            i += 1
            continue
        
        current_name = sql_text[name_start:i]
        
        # Пропускаем пробелы до AS
        while i < length and sql_text[i].isspace():
            i += 1
        
        # Проверяем AS (регистронезависимо)
        if i + 1 < length and sql_text[i:i+2].upper() == 'AS':
            i += 2
        else:
            continue
        
        # Пропускаем пробелы до открывающей скобки
        while i < length and sql_text[i].isspace():
            i += 1
        
        if i >= length or sql_text[i] != '(':
            continue
        
        # Нашли нужный CTE
        if current_name.upper() == cte_name.upper():
            # Начинаем собирать CTE текст
            cte_start = name_start
            
            # Ищем закрывающую скобку с учетом вложенности
            paren_count = 1
            j = i + 1
            in_single_quote_cte = False
            in_double_quote_cte = False
            
            while j < length and paren_count > 0:
                # Пропускаем комментарии внутри CTE
                if j + 1 < length and sql_text[j:j+2] == '--':
                    while j < length and sql_text[j] != '\n':
                        j += 1
                    continue
                elif j + 1 < length and sql_text[j:j+2] == '/*':
                    j += 2
                    while j + 1 < length and sql_text[j:j+2] != '*/':
                        j += 1
                    j += 2
                    continue
                
                # Обработка кавычек
                if sql_text[j] == "'" and not in_double_quote_cte:
                    in_single_quote_cte = not in_single_quote_cte
                elif sql_text[j] == '"' and not in_single_quote_cte:
                    in_double_quote_cte = not in_double_quote_cte
                
                if not (in_single_quote_cte or in_double_quote_cte):
                    if sql_text[j] == '(':
                        paren_count += 1
                    elif sql_text[j] == ')':
                        paren_count -= 1
                
                j += 1
            
            # Теперь ищем запятую или конец CTE блока
            k = j
            while k < length and sql_text[k].isspace():
                k += 1
            
            cte_end = k
            if k < length and sql_text[k] == ',':
                cte_end = k + 1  # Включаем запятую
            else:
                # Это последний CTE, ищем SELECT
                cte_end = k
            
            return (sql_text[cte_start:cte_end].strip(), cte_start, cte_end)
        
        # Ищем конец текущего CTE, чтобы перейти к следующему
        paren_count = 1
        j = i + 1
        in_single_quote_cte = False
        in_double_quote_cte = False
        
        while j < length and paren_count > 0:
            if j + 1 < length and sql_text[j:j+2] == '--':
                while j < length and sql_text[j] != '\n':
                    j += 1
                continue
            elif j + 1 < length and sql_text[j:j+2] == '/*':
                j += 2
                while j + 1 < length and sql_text[j:j+2] != '*/':
                    j += 1
                j += 2
                continue
            
            if sql_text[j] == "'" and not in_double_quote_cte:
                in_single_quote_cte = not in_single_quote_cte
            elif sql_text[j] == '"' and not in_single_quote_cte:
                in_double_quote_cte = not in_double_quote_cte
            
            if not (in_single_quote_cte or in_double_quote_cte):
                if sql_text[j] == '(':
                    paren_count += 1
                elif sql_text[j] == ')':
                    paren_count -= 1
            
            j += 1
        
        i = j
        
        # Пропускаем запятую если есть
        while i < length and sql_text[i].isspace():
            i += 1
        if i < length and sql_text[i] == ',':
            i += 1
    
    return (None, -1, -1)

def _get_mat_value(raw_val) -> Optional[str]:
    """Извлечь значение материализации из сырого значения.

    Поддерживает форматы:
    - "ephemeral" (строка)
    - {"value": "stage_calcid"} (словарь)
    - {"value": "stage_calcid", "source": "..."} (словарь с метаданными)
    """
    if raw_val is None:
        return None
    if isinstance(raw_val, str):
        return raw_val if raw_val else None
    if isinstance(raw_val, dict):
        return raw_val.get("value")
    return None


def get_effective_materialization(
    cte_name: str,
    ctx: str,
    tool: str,
    cte_config: dict,
) -> Optional[str]:
    """Определить итоговую материализацию для конкретного ctx+tool.

    Логика: by_tool + by_context + default
    Объединение "И" - если есть и то и другое, результат конкатенируется.
    """
    if not cte_config:
        return None

    cte_mat = cte_config.get("cte_materialization", {})
    by_tool = cte_mat.get("by_tool", {})
    by_context = cte_mat.get("by_context", {})
    default_raw = cte_mat.get("default")
    default = _get_mat_value(default_raw)

    result = None

    tool_val_raw = by_tool.get(tool)
    ctx_val_raw = by_context.get(ctx)

    tool_val = _get_mat_value(tool_val_raw)
    ctx_val = _get_mat_value(ctx_val_raw)

    if tool_val and ctx_val:
        result = f"{tool_val}_{ctx_val}"
    elif tool_val:
        result = tool_val
    elif ctx_val:
        result = ctx_val

    if result is None:
        result = default

    return result


def is_materialized(cte_materialization: Optional[str]) -> bool:
    """Проверить, является ли материализация признаком материализации CTE."""
    if cte_materialization is None:
        return False
    if isinstance(cte_materialization, str):
        return cte_materialization.lower() not in ("", "ephemeral")
    return False


def get_cte_order(parent_sql: str) -> List[Tuple[str, int]]:
    """Получить порядок CTE в запросе с их позициями.

    Returns:
        List[(cte_name, start_position)] отсортировано по позиции
    """
    cte_info = []
    pattern = re.compile(r"\b([a-zA-Z0-9_]+)\s+as\s*\(", re.IGNORECASE)

    with_match = re.search(r"\bWITH\s+", parent_sql, re.IGNORECASE)
    if not with_match:
        return []

    search_start = with_match.end()
    for match in pattern.finditer(parent_sql[search_start:]):
        cte_name = match.group(1)
        start_pos = search_start + match.start()
        cte_info.append((cte_name, start_pos))

    cte_info.sort(key=lambda x: x[1])
    return cte_info


def extract_cte_query_full(parent_sql: str, cte_name: str) -> Optional[str]:
    """Извлечь полный запрос CTE с WITH секцией для зависимых не-материализуемых CTE.

    Returns:
        SQL запрос для CTE (может включать WITH для зависимых CTE)
    """
    parser = SQLMetadataParser()
    return parser.extract_cte_query(parent_sql, cte_name)


def extract_cte_source_tables(parent_sql: str, cte_name: str) -> Set[str]:
    """Извлечь таблицы-источники для конкретного CTE."""
    parser = SQLMetadataParser()
    cte_data = parser.extract_cte(parent_sql)
    return cte_data.get(cte_name, {}).get("source_tables", set())


def get_cte_dependencies(parent_sql: str, cte_name: str) -> Set[str]:
    """Получить список CTE, от которых зависит указанное CTE."""
    parser = SQLMetadataParser()
    cte_data = parser.extract_cte(parent_sql)
    return cte_data.get(cte_name, {}).get("source_ctes", set())


def build_cte_sql_with_deps(
    parent_sql: str,
    cte_name: str,
    materialized_ctes: Set[str],
    all_cte_names: Set[str],
) -> str:
    """Построить SQL для CTE с включением зависимых не-материализуемых CTE.

    Args:
        parent_sql: исходный SQL родительского запроса
        cte_name: имя CTE для которого строим запрос
        materialized_ctes: множество материализованных CTE
        all_cte_names: все имена CTE в родительском запросе

    Returns:
        SQL запрос для CTE (может включать WITH для зависимых не-материализованных CTE)
    """
    deps = get_cte_dependencies(parent_sql, cte_name)

    non_mat_deps = deps - materialized_ctes

    if not non_mat_deps:
        return extract_cte_query_full(parent_sql, cte_name) or ""

    with_parts = []

    for dep_name in non_mat_deps:
        dep_query = extract_cte_query_full(parent_sql, dep_name)
        if dep_query:
            with_parts.append(f"{dep_name} AS ({dep_query})")

    main_query = extract_cte_query_full(parent_sql, cte_name)

    if with_parts:
        return f"WITH {', '.join(with_parts)}\n{main_query}"
    else:
        return main_query


def update_cte_sql_with_workflow_refs(
    cte_sql: str,
    cte_name: str,
    materialized_ctes_order: List[str],
    temp_cte_objects: Dict[str, SQLObjectModel],
) -> str:
    """Обновить SQL CTE, заменив ссылки на другие материализованные CTE.

    Args:
        cte_sql: исходный SQL CTE
        cte_name: имя текущего CTE
        materialized_ctes_order: порядок материализованных CTE (b, a, ...)
        temp_cte_objects: словарь уже созданных CTE объектов

    Returns:
        Обновлённый SQL с заменёнными ссылками
    """
    result = cte_sql

    cte_deps = get_cte_dependencies("", cte_name)
    for dep_name in cte_deps:
        if dep_name in temp_cte_objects:
            wf_ref = get_workflow_ref_path(temp_cte_objects[dep_name])
            result = replace_cte_references(result, {dep_name: wf_ref})

    return result


def replace_cte_references(
    sql: str,
    cte_replacements: Dict[str, str],
) -> str:
    """Заменить обращения к CTE на workflow_ref.

    Заменяет:
    - FROM cte_name -> FROM _w.path.to.cte
    - JOIN cte_name -> JOIN _w.path.to.cte
    - ,cte_name -> ,_w.path.to.cte
    """
    result = sql

    for cte_name, workflow_ref in cte_replacements.items():
        pattern = re.compile(
            r"\b(FROM|JOIN|,)\s+(" + re.escape(cte_name) + r")\b", re.IGNORECASE
        )
        result = pattern.sub(rf"\1 {workflow_ref}", result)

    return result


def remove_cte_from_with(
    parent_sql: str,
    cte_names_to_remove: Set[str],
) -> Tuple[str, bool]:
    """Удалить определения CTE из WITH секции.

    Args:
        parent_sql: исходный SQL
        cte_names_to_remove: имена CTE для удаления

    Returns:
        (обновленный SQL, есть ли еще CTE в WITH)
    """
    if not cte_names_to_remove:
        return parent_sql, True

    cte_order = get_cte_order(parent_sql)
    if not cte_order:
        return parent_sql, False

    with_match = re.search(r"\bWITH\s+", parent_sql, re.IGNORECASE)

    if not with_match:
        return parent_sql, False

    with_start = with_match.start()
    with_end = with_match.end()
    remaining_ctes = [
        (name, pos) for name, pos in cte_order if name not in cte_names_to_remove
    ]

    if not remaining_ctes:
        return get_main_sql(parent_sql)[0], False

    new_with_parts = []
    for cte_name, _ in remaining_ctes:
        print(f"!!!!! get_with_by_name: {get_with_by_name(cte_name)}")
        cte_def = extract_cte_query_full(parent_sql, cte_name)
        if cte_def:
            new_with_parts.append(f"{cte_name} AS ({cte_def})")

    main_query_match = re.search(
        r"\)\s*select\s+", parent_sql[with_end:], re.IGNORECASE
    )
    if main_query_match:
        main_query_start = with_end + main_query_match.start() + 1
        while (
            main_query_start < len(parent_sql)
            and parent_sql[main_query_start].isspace()
        ):
            main_query_start += 1
    else:
        main_query_start = with_end

    main_query = parent_sql[main_query_start:]

    result = f"WITH {', '.join(new_with_parts)}\n{main_query}"
    return result, True


def create_cte_sql_object(
    parent_sql_object: SQLObjectModel,
    cte_name: str,
    cte_sql: str,
    cte_config: dict,
    all_ctes: Dict[str, Dict[str, Any]],
    materialized_ctes: Set[str],
    cte_index: int,
    ctx: str,
    tool: str,
    tools_by_context: Dict[str, List[str]],
    all_contexts: List[str],
) -> SQLObjectModel:
    """Создать SQLObjectModel для материализованного CTE.

    Args:
        parent_sql_object: родительский SQL объект
        cte_name: имя CTE
        cte_sql: SQL запрос CTE (может включать WITH для зависимых не-материализованных CTE)
        cte_config: конфиг CTE из родительского объекта
        all_ctes: все CTE родительского объекта
        materialized_ctes: множество материализованных CTE
        cte_index: порядковый номер CTE (1, 2, ...)
        ctx: контекст
        tool: инструмент
        tools_by_context: маппинг контекстов на инструменты
        all_contexts: все контексты

    Returns:
        SQLObjectModel для CTE
    """
    parent_path = parent_sql_object.path
    if parent_path.endswith(".sql"):
        parent_path = parent_path[:-4]

    new_path = f"{parent_path}.{cte_index}.cte.{cte_name}.sql"
    new_name = f"{parent_sql_object.name}.{cte_index}.cte.{cte_name}"

    parser = SQLMetadataParser()
    metadata = parser.parse(cte_sql)

    cte_obj = SQLObjectModel(
        path=new_path,
        name=new_name,
        source_sql=cte_sql,
        metadata=metadata,
        generated=True,
    )

    cte_obj.config = _build_cte_config(
        parent_config=parent_sql_object.config,
        cte_config=cte_config,
        cte_name=cte_name,
        tools_by_context=tools_by_context,
    )

    cte_obj.compiled = _build_cte_compiled(
        cte_obj=cte_obj,
        ctx=ctx,
        tool=tool,
        tools_by_context=tools_by_context,
        all_contexts=all_contexts,
    )

    return cte_obj


def _build_cte_config(
    parent_config: Dict[str, Dict[str, ConfigValue]],
    cte_config: dict,
    cte_name: str,
    effective_materialization: Optional[Dict[str, List[str]]] = None,
    tools_by_context: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Построить config для CTE объекта.

    Наследует от родительского + merge с cte_config.
    Для всех контекстов из parent_config добавляется запись.
    Для контекстов с материализацией - полный конфиг.
    Для контекстов без материализации - только enabled: false.
    """
    result = {}
    tools_by_context = tools_by_context or {}

    if not effective_materialization:
        effective_materialization = {}

    for ctx, ctx_config in parent_config.items():
        result[ctx] = {}

        materialized_tools = effective_materialization.get(ctx, [])
        if materialized_tools:
            result[ctx]["materialization"] = ConfigValue(
                value="stage_calcid",
                source="cte_config",
                file=None,
            )

            cte_attrs = cte_config.get("attributes", [])
            if cte_attrs:
                result[ctx]["attributes"] = cte_attrs

            result[ctx]["tools"] = materialized_tools
        else:
            result[ctx]["enabled"] = ConfigValue(
                value=False,
                source="default",
                file=None,
                reason=f"CTE {cte_name} does not materialize for this context",
            )

    return result


def _build_cte_compiled(
    cte_obj: SQLObjectModel,
    ctx: str,
    tool: str,
    tools_by_context: Dict[str, List[str]],
    all_contexts: List[str],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Построить compiled для CTE объекта."""
    compiled = {}

    for c in all_contexts:
        tools = tools_by_context.get(c, [])

        compiled[c] = {}
        for t in tools:
            workflow_refs = (
                {ref: "" for ref in cte_obj.metadata.workflow_refs.keys()}
                if cte_obj.metadata and cte_obj.metadata.workflow_refs
                else {}
            )
            model_refs = (
                {ref: "" for ref in cte_obj.metadata.model_refs.keys()}
                if cte_obj.metadata and cte_obj.metadata.model_refs
                else {}
            )
            parameters = (
                sorted(list(cte_obj.metadata.parameters))
                if cte_obj.metadata and cte_obj.metadata.parameters
                else []
            )

            compiled[c][t] = {
                "target_table": "",
                "workflow_refs": workflow_refs,
                "model_refs": model_refs,
                "parameters": parameters,
                "prepared_sql": cte_obj.source_sql,
                "rendered_sql": "",
            }

    return compiled


def get_workflow_ref_path(cte_obj: SQLObjectModel) -> str:
    """Получить workflow_ref путь для CTE объекта.

    Пример: _w.folder.subfolder.query.1.cte.cteName
    """
    path = cte_obj.path
    if path.endswith(".sql"):
        path = path[:-4]

    if path.startswith("SQL/"):
        path = path[4:]

    path_parts = path.split("/")
    dot_path = ".".join(path_parts)

    return f"_w.{dot_path}"


def process_cte_materialization(
    sql_objects: Dict[str, SQLObjectModel],
    config,
    model_contexts: List[str],
    tools_by_context: Dict[str, List[str]],
    default_materialization: str,
) -> Dict[str, SQLObjectModel]:
    """Обработать материализацию CTE.

    Для каждого SQL объекта:
    1. Проверить наличие CTE с материализацией, отличной от ephemeral
    2. Создать новые SQL объекты для материализованных CTE
    3. Обновить prepared_sql родительских объектов

    Args:
        sql_objects: словарь SQL объектов
        config: конфиг модели
        model_contexts: все контексты модели
        tools_by_context: маппинг контекстов на инструменты
        default_materialization: дефолтная материализация

    Returns:
        Словарь новых SQL объектов для материализованных CTE
    """
    from FW.generation.sql_object_config import (
        build_sql_object_config,
        build_compiled_sql_object,
    )

    new_cte_objects: Dict[str, SQLObjectModel] = {}
    all_tools = set()
    for tools in tools_by_context.values():
        all_tools.update(tools)

    for sql_key, sql_obj in sql_objects.items():
        if sql_obj.generated:
            continue

        if not sql_obj.metadata or not sql_obj.metadata.cte:
            continue

        all_cte_names = set(sql_obj.metadata.cte.keys())
        if not all_cte_names:
            continue

        parent_config = sql_obj.config
        cte_order_raw = get_cte_order(sql_obj.source_sql)
        all_cte_order_names = [name for name, _ in cte_order_raw]

        materialization_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for ctx in model_contexts:
            if ctx not in parent_config:
                continue

            ctx_config = parent_config[ctx]
            cte_queries_config = ctx_config.get("cte", {}).get("cte_queries", {})

            if not cte_queries_config:
                continue

            tools = tools_by_context.get(ctx, [])

            for tool in tools:
                for cte_name in all_cte_order_names:
                    if cte_name not in all_cte_names:
                        continue
                    cte_cfg = cte_queries_config.get(cte_name, {})
                    if not cte_cfg:
                        continue

                    mat = get_effective_materialization(cte_name, ctx, tool, cte_cfg)

                    if is_materialized(mat):
                        if cte_name not in materialization_map:
                            materialization_map[cte_name] = {}
                        if ctx not in materialization_map[cte_name]:
                            materialization_map[cte_name][ctx] = {
                                "tools": set(),
                                "config": {},
                            }
                        materialization_map[cte_name][ctx]["tools"].add(tool)
                        materialization_map[cte_name][ctx]["config"] = cte_cfg

        if not materialization_map:
            continue

        cte_indices = {}
        for i, cte_name in enumerate(materialization_map.keys(), start=1):
            cte_indices[cte_name] = i

        materialized_ctes_global: Dict[str, Dict[str, str]] = {}

        for cte_name, ctx_tools in materialization_map.items():
            parent_path = sql_obj.path
            if parent_path.endswith(".sql"):
                parent_path = parent_path[:-4]

            cte_path = f"{parent_path}.{cte_indices[cte_name]}.cte.{cte_name}.sql"
            cte_name_full = f"{sql_obj.name}.{cte_indices[cte_name]}.cte.{cte_name}"

            cte_sql = build_cte_sql_with_deps(
                parent_sql=sql_obj.source_sql,
                cte_name=cte_name,
                materialized_ctes=set(materialization_map.keys()),
                all_cte_names=all_cte_names,
            )

            parser = SQLMetadataParser()
            metadata = parser.parse(cte_sql)

            cte_obj = SQLObjectModel(
                path=cte_path,
                name=cte_name_full,
                source_sql=cte_sql,
                metadata=metadata,
                generated=True,
            )

            effective_materialization: Dict[str, List[str]] = {}
            ctx_tools_data = ctx_tools

            first_ctx = None
            cte_cfg = {}
            for k in ctx_tools_data.keys():
                if k != "config":
                    first_ctx = k
                    cte_cfg = ctx_tools_data.get(k, {}).get("config", {})
                    break

            for ctx in ctx_tools_data.keys():
                if ctx == "config":
                    continue
                tools = ctx_tools_data.get(ctx, {}).get("tools", set())
                effective_materialization[ctx] = []
                for tool in tools:
                    mat = get_effective_materialization(cte_name, ctx, tool, cte_cfg)
                    if is_materialized(mat):
                        effective_materialization[ctx].append(tool)

            cte_obj.config = _build_cte_config(
                parent_config=parent_config,
                cte_config=cte_cfg,
                cte_name=cte_name,
                effective_materialization=effective_materialization,
                tools_by_context=tools_by_context,
            )

            compiled: Dict[str, Dict[str, Dict[str, Any]]] = {}
            for ctx in ctx_tools_data.keys():
                if ctx == "config":
                    continue
                tools = ctx_tools_data.get(ctx, {}).get("tools", set())
                compiled[ctx] = {}
                for tool in tools:
                    workflow_refs = (
                        {ref: "" for ref in metadata.workflow_refs.keys()}
                        if metadata.workflow_refs
                        else {}
                    )
                    model_refs = (
                        {ref: "" for ref in metadata.model_refs.keys()}
                        if metadata.model_refs
                        else {}
                    )
                    parameters = (
                        sorted(list(metadata.parameters)) if metadata.parameters else []
                    )
                    compiled[ctx][tool] = {
                        "target_table": "",
                        "workflow_refs": workflow_refs,
                        "model_refs": model_refs,
                        "parameters": parameters,
                        "prepared_sql": cte_obj.source_sql,
                        "rendered_sql": "",
                    }
            cte_obj.compiled = compiled

            new_cte_objects[cte_path] = cte_obj

            materialized_ctes_global[cte_name] = {}
            for ctx in ctx_tools_data.keys():
                if ctx == "config":
                    continue
                tools = ctx_tools_data.get(ctx, {}).get("tools", set())
                for tool in tools:
                    wf_ref = get_workflow_ref_path(cte_obj)
                    materialized_ctes_global[cte_name][f"{ctx}_{tool}"] = wf_ref

            cte_deps = get_cte_dependencies(sql_obj.source_sql, cte_name)
            deps_in_map = [d for d in cte_deps if d in materialization_map]
            if deps_in_map:
                for dep_name in deps_in_map:
                    dep_path = (
                        f"{parent_path}.{cte_indices[dep_name]}.cte.{dep_name}.sql"
                    )
                    if dep_path in new_cte_objects:
                        dep_wf_ref = get_workflow_ref_path(new_cte_objects[dep_path])
                        cte_obj.source_sql = replace_cte_references(
                            cte_obj.source_sql, {dep_name: dep_wf_ref}
                        )
                        if cte_obj.metadata:
                            cte_obj.metadata.workflow_refs[dep_wf_ref] = {
                                "path": dep_wf_ref,
                                "parts": dep_wf_ref.split("."),
                                "query_name": dep_name,
                                "folder": ".".join(dep_wf_ref.split(".")[2:-2])
                                if len(dep_wf_ref.split(".")) > 3
                                else "",
                                "full_ref": dep_wf_ref,
                            }
                        for ctx_key in cte_obj.compiled:
                            for tool_key in cte_obj.compiled[ctx_key]:
                                cte_obj.compiled[ctx_key][tool_key]["prepared_sql"] = (
                                    cte_obj.source_sql
                                )
                                if (
                                    dep_wf_ref
                                    not in cte_obj.compiled[ctx_key][tool_key][
                                        "workflow_refs"
                                    ]
                                ):
                                    cte_obj.compiled[ctx_key][tool_key][
                                        "workflow_refs"
                                    ][dep_wf_ref] = ""

        for ctx in model_contexts:
            if ctx not in parent_config:
                continue

            ctx_config = parent_config[ctx]
            cte_queries_config = ctx_config.get("cte", {}).get("cte_queries", {})

            if not cte_queries_config:
                continue

            tools = tools_by_context.get(ctx, [])

            ctes_to_remove = set()
            for cte_name in materialization_map:
                if ctx in materialization_map[cte_name]:
                    ctes_to_remove.add(cte_name)

            if not ctes_to_remove:
                continue

            materialized_for_ctx_tool: Dict[str, str] = {}
            for cte_name in ctes_to_remove:
                key = f"{ctx}_{list(tools)[0]}"
                if key in materialized_ctes_global.get(cte_name, {}):
                    wf_ref = materialized_ctes_global[cte_name][key]
                    materialized_for_ctx_tool[cte_name] = wf_ref

            for tool in tools:
                tool_key = f"{ctx}_{tool}"
                materialized_for_tool: Dict[str, str] = {}
                ctes_to_replace = {}
                for cte_name in ctes_to_remove:
                    wf_key = f"{ctx}_{tool}"
                    if wf_key in materialized_ctes_global.get(cte_name, {}):
                        wf_ref = materialized_ctes_global[cte_name][wf_key]
                        materialized_for_tool[cte_name] = wf_ref
                        sql_obj.compiled[ctx][tool]["workflow_refs"][wf_ref] = ""
                        ctes_to_replace[cte_name] = wf_ref

                if not materialized_for_tool:
                    continue

                base_prepared_sql = sql_obj.source_sql
                if ctx in sql_obj.compiled and tool in sql_obj.compiled[ctx]:
                    base_prepared_sql = sql_obj.compiled[ctx][tool].get(
                        "prepared_sql", sql_obj.source_sql
                    )

                prepared_sql = remove_cte_from_with(base_prepared_sql, ctes_to_remove)[
                    0
                ]
                if ctes_to_replace:
                   prepared_sql = replace_cte_references(prepared_sql, ctes_to_replace)
                if ctx not in sql_obj.compiled:
                    continue
                if tool not in sql_obj.compiled[ctx]:
                    continue

                sql_obj.compiled[ctx][tool]["prepared_sql"] = prepared_sql

    return new_cte_objects
