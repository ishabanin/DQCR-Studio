"""SQL metadata model."""

import re
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field


SQL_KEYWORDS = {
    "AS",
    "AND",
    "OR",
    "NOT",
    "IN",
    "IS",
    "NULL",
    "TRUE",
    "FALSE",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "SELECT",
    "FROM",
    "WHERE",
    "GROUP",
    "BY",
    "ORDER",
    "HAVING",
    "JOIN",
    "INNER",
    "LEFT",
    "RIGHT",
    "OUTER",
    "CROSS",
    "ON",
    "UNION",
    "ALL",
    "DISTINCT",
    "LIMIT",
    "OFFSET",
    "BETWEEN",
    "LIKE",
    "EXISTS",
    "ANY",
    "SOME",
    "ASC",
    "DESC",
    "NULLS",
    "FIRST",
    "LAST",
    "WITH",
    "RECURSIVE",
    "OVER",
    "PARTITION",
    "ROW",
    "ROWS",
    "RANGE",
    "PRECEDING",
    "FOLLOWING",
    "CURRENT",
    "UNBOUNDED",
    "VALUES",
    "INSERT",
    "UPDATE",
    "DELETE",
    "SET",
    "INTO",
    "CREATE",
    "ALTER",
    "DROP",
    "TABLE",
    "INDEX",
    "VIEW",
    "PRIMARY",
    "KEY",
    "FOREIGN",
    "REFERENCES",
    "CONSTRAINT",
    "DEFAULT",
    "CHECK",
    "UNIQUE",
    "CASCADE",
    "GRANT",
    "REVOKE",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "FETCH",
    "NEXT",
    "ONLY",
    "PERCENT",
    "TIES",
    "FOR",
    "OF",
    "NO",
    "NOWAIT",
    "SKIP",
    "LOCKED",
    "LATERAL",
    "NATURAL",
    "USING",
    "MATERIALIZED",
    "EXTEND",
    "MINUS",
    "INTERSECT",
    "SUBMULTISET",
    "MULTISET",
}


@dataclass
class SQLMetadata:
    """Метаданные SQL запроса."""

    parameters: Set[str] = field(default_factory=set)
    tables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    aliases: List[Dict[str, str]] = field(default_factory=list)
    cte: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    model_refs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    workflow_refs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    inline_query_config: Optional[Dict[str, Any]] = field(default=None)
    inline_cte_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    inline_attr_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    project_props: Dict[str, Any] = field(default_factory=dict)
    context_flags: Dict[str, Any] = field(default_factory=dict)
    context_constants: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "parameters": sorted(self.parameters),
            "tables": self.tables,
            "aliases": self.aliases,
            "cte": {
                name: {
                    "source_tables": sorted(info.get("source_tables", [])),
                    "source_ctes": sorted(info.get("source_ctes", [])),
                }
                for name, info in self.cte.items()
            },
            "functions": self.functions,
            "model_refs": self.model_refs,
            "workflow_refs": self.workflow_refs,
            "inline_query_config": self.inline_query_config,
            "inline_cte_configs": self.inline_cte_configs,
            "inline_attr_configs": self.inline_attr_configs,
            "project_props": self.project_props,
            "context_flags": self.context_flags,
            "context_constants": self.context_constants,
        }


class SQLMetadataParser:
    """Парсер SQL для извлечения метаданных."""

    VARIABLE_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")

    FROM_PATTERN = re.compile(
        r"\bFROM\s+(?:(\{\{[^}]+\}\})|([a-zA-Z0-9_\.]+))(?:\s+(?:as\s+)?([a-zA-Z0-9_]+))?",
        re.IGNORECASE,
    )

    JOIN_PATTERN = re.compile(
        r"\b(?:INNER|LEFT|RIGHT|OUTER|CROSS)?\s*JOIN\s+(?:(\{\{[^}]+\}\})|([a-zA-Z0-9_\.]+))(?:\s+(?:as\s+)?([a-zA-Z0-9_]+))?",
        re.IGNORECASE,
    )

    CTE_WITH_PATTERN = re.compile(r"\bWITH\s+", re.IGNORECASE)
    CTE_DEF_PATTERN = re.compile(r"\b([a-zA-Z0-9_]+)\s+as\s*\(", re.IGNORECASE)
    CTE_SOURCE_VAR_PATTERN = re.compile(r"\bfrom\s+\{\{([^}]+)\}\}", re.IGNORECASE)
    CTE_SOURCE_CTE_PATTERN = re.compile(
        r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE
    )

    MODEL_REF_PATTERN = re.compile(r"_m\.[a-zA-Z_][a-zA-Z0-9_.-]*")
    WORKFLOW_REF_PATTERN = re.compile(r"_w\.[a-zA-Z0-9_][a-zA-Z0-9_.-]+")

    PROJECT_PROP_PATTERN = re.compile(r"_p\.props\.([A-Za-z_][A-Za-z0-9_]*)")
    CONTEXT_FLAG_PATTERN = re.compile(
        r"_ctx\.flags\.([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
    )
    CONTEXT_CONST_PATTERN = re.compile(r"_ctx\.const\.([A-Za-z_][A-Za-z0-9_]*)")

    SELECT_FIELD_PATTERN = re.compile(
        r"\bSELECT\s+(?:DISTINCT\s+)?(.+?)(?=\bFROM\b|\bGROUP BY\b|\bORDER BY\b|\bLIMIT\b|\bWHERE\b|$)",
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self, exclude_vars: Set[str] = None):
        self.exclude_vars = exclude_vars or set()

    def extract_parameters(self, sql_content: str, table_aliases: Set[str]) -> Set[str]:
        """Извлечь параметры-значения."""
        matches = self.VARIABLE_PATTERN.findall(sql_content)
        parameters = set()
        known_aliases_lower = {a.lower() for a in table_aliases}

        for match in matches:
            match = match.strip()
            dot_idx = match.find(".")
            if dot_idx > 0:
                var_name = match[:dot_idx]
            else:
                var_name = match.split("|")[0].strip()

            if var_name.lower() in known_aliases_lower:
                continue

            parameters.add(match)

        return parameters

    def extract_tables(
        self, sql_content: str, cte_names: Set[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Извлечь таблицы."""
        tables = {}
        cte_names = cte_names or set()

        for match in self.FROM_PATTERN.finditer(sql_content):
            var_table = match.group(1)
            literal_table = match.group(2)
            alias = match.group(3)

            if alias and (
                not alias[0].isalpha()
                and alias[0] != "_"
                or alias.upper() in SQL_KEYWORDS
            ):
                alias = None

            if var_table:
                table_name = var_table.replace("{{", "").replace("}}", "").strip()
                tables[table_name] = {
                    "alias": (alias or table_name).lower(),
                    "is_variable": True,
                    "is_cte": False,
                }
            elif literal_table:
                is_cte = literal_table.lower() in {c.lower() for c in cte_names}
                tables[literal_table] = {
                    "alias": (alias or literal_table).lower(),
                    "is_variable": False,
                    "is_cte": is_cte,
                }

        for match in self.JOIN_PATTERN.finditer(sql_content):
            var_table = match.group(1)
            literal_table = match.group(2)
            alias = match.group(3)

            if alias and (
                not alias[0].isalpha()
                and alias[0] != "_"
                or alias.upper() in SQL_KEYWORDS
            ):
                alias = None

            if var_table:
                table_name = var_table.replace("{{", "").replace("}}", "").strip()
                tables[table_name] = {
                    "alias": (alias or table_name).lower(),
                    "is_variable": True,
                    "is_cte": False,
                }
            elif literal_table:
                is_cte = literal_table.lower() in {c.lower() for c in cte_names}
                tables[literal_table] = {
                    "alias": (alias or literal_table).lower(),
                    "is_variable": False,
                    "is_cte": is_cte,
                }

        return tables

    def extract_cte(self, sql_content: str) -> Dict[str, Dict[str, Any]]:
        """Извлечь CTE определения."""
        cte_info = {}
        cte_match = self.CTE_WITH_PATTERN.search(sql_content)
        if not cte_match:
            return cte_info

        content_after_with = sql_content[cte_match.end() :]
        cte_def_matches = list(self.CTE_DEF_PATTERN.finditer(content_after_with))

        for i, name_match in enumerate(cte_def_matches):
            cte_name = name_match.group(1)
            start_pos = name_match.end() - 1
            paren_depth = 0
            end_pos = -1

            for j, char in enumerate(content_after_with[start_pos:]):
                if char == "(":
                    paren_depth += 1
                elif char == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        end_pos = start_pos + j + 1
                        break

            if end_pos == -1:
                continue

            if i + 1 < len(cte_def_matches):
                next_start = cte_def_matches[i + 1].start()
                if next_start < end_pos:
                    end_pos = next_start

            cte_block = content_after_with[name_match.start() : end_pos]
            source_tables = set()
            source_ctes = set()

            for m in self.CTE_SOURCE_VAR_PATTERN.finditer(cte_block):
                source_tables.add(m.group(1))

            for m in self.CTE_SOURCE_CTE_PATTERN.finditer(cte_block):
                potential_cte = m.group(1)
                if potential_cte.upper() not in SQL_KEYWORDS:
                    source_ctes.add(potential_cte)

            match = re.search(
                r"\b[a-zA-Z0-9_]+\s+as\s*\((.+)\)", cte_block, re.IGNORECASE | re.DOTALL
            )
            cte_source_sql = match.group(1).strip() if match else cte_block

            cte_info[cte_name] = {
                "source_tables": source_tables,
                "source_ctes": source_ctes,
                "cte_source_sql": cte_source_sql,
            }

        return cte_info

    def extract_cte_query(self, sql_content: str, cte_name: str) -> Optional[str]:
        """Извлечь SELECT-часть конкретного CTE.

        Args:
            sql_content: Полный SQL с WITH-секцией
            cte_name: Имя CTE

        Returns:
            Внутренний SELECT CTE (без скобок) или None если не найден
        """
        cte_match = self.CTE_WITH_PATTERN.search(sql_content)
        if not cte_match:
            return None

        content_after_with = sql_content[cte_match.end() :]
        cte_def_matches = list(self.CTE_DEF_PATTERN.finditer(content_after_with))

        target_idx = -1
        target_cte_start = None
        for idx, name_match in enumerate(cte_def_matches):
            if name_match.group(1).lower() == cte_name.lower():
                target_idx = idx
                target_cte_start = name_match
                break

        if not target_cte_start:
            return None

        start_pos = target_cte_start.end() - 1

        paren_depth = 0
        end_pos = -1

        for j, char in enumerate(content_after_with[start_pos:]):
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
                if paren_depth == 0:
                    end_pos = start_pos + j + 1
                    break

        if end_pos == -1:
            return None

        if target_idx >= 0 and target_idx + 1 < len(cte_def_matches):
            next_start = cte_def_matches[target_idx + 1].start()
            if next_start < end_pos:
                end_pos = next_start

        cte_block = content_after_with[target_cte_start.start() : end_pos]

        match = re.search(
            r"\b[a-zA-Z0-9_]+\s+as\s*\((.+)\)", cte_block, re.IGNORECASE | re.DOTALL
        )
        if match:
            return match.group(1).strip()

        return None

    def extract_functions(self, sql_content: str) -> List[Dict[str, Any]]:
        """Извлечь функции."""
        functions = []

        comment_blocks = []
        for m in re.finditer(r"/\*.*?\*/", sql_content, re.DOTALL):
            comment_blocks.append((m.start(), m.end()))
        for m in re.finditer(r"--.*?$", sql_content, re.MULTILINE):
            comment_blocks.append((m.start(), m.end()))

        func_name_pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

        for match in func_name_pattern.finditer(sql_content):
            func_pos = match.start()

            is_in_comment = any(
                start <= func_pos < end for start, end in comment_blocks
            )
            if is_in_comment:
                continue

            func_name = match.group(1).upper()
            if func_name in SQL_KEYWORDS or func_name.isdigit():
                continue

            start_paren = match.end() - 1
            end_paren = self._find_closing_paren(sql_content, start_paren)
            if end_paren == -1:
                continue

            params_str = sql_content[start_paren + 1 : end_paren]
            params = self._split_params(params_str)
            functions.append({"name": func_name, "params": params})

        return functions

    def _find_closing_paren(self, sql_content: str, start_paren: int) -> int:
        """Найти позицию закрывающей скобки."""
        if start_paren >= len(sql_content) or sql_content[start_paren] != "(":
            return -1

        depth = 0
        i = start_paren
        while i < len(sql_content):
            if sql_content[i] == "(":
                depth += 1
            elif sql_content[i] == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    def _split_params(self, params_str: str) -> List[str]:
        """Разделить параметры по запятым."""
        params = []
        current = ""
        depth = 0

        for char in params_str:
            if char == "(":
                depth += 1
                current += char
            elif char == ")":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                if current.strip():
                    params.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            params.append(current.strip())

        return params

    def _find_main_query_start(self, sql_content: str, after_with: int) -> int:
        """Найти начало основного SELECT после CTE."""
        depth = 0
        i = after_with
        while i < len(sql_content):
            if sql_content[i] == "(":
                depth += 1
            elif sql_content[i] == ")":
                depth -= 1
                if depth == 0:
                    while i + 1 < len(sql_content) and sql_content[i + 1].isspace():
                        i += 1
                if (
                    i + 1 < len(sql_content)
                    and sql_content[i + 1 : i + 7].upper() == "SELECT"
                ):
                    while i < len(sql_content) and sql_content[i].isspace():
                        i += 1
                    return i
            i += 1
        return after_with

    def extract_field_aliases(
        self, sql_content: str, known_aliases: Set[str]
    ) -> List[Dict[str, str]]:
        """Извлечь алиасы полей из SELECT."""
        aliases = []

        cte_match = self.CTE_WITH_PATTERN.search(sql_content)
        search_start = 0
        if cte_match:
            search_start = self._find_main_query_start(sql_content, cte_match.end())

        if search_start > 0:
            select_content_match = self.SELECT_FIELD_PATTERN.search(
                sql_content[search_start:]
            )
        else:
            select_content_match = self.SELECT_FIELD_PATTERN.search(sql_content)

        if not select_content_match:
            return aliases

        select_content = select_content_match.group(1)
        from FW.parsing.inline_config_parser import remove_inline_configs

        select_content = remove_inline_configs(select_content)
        fields = self._split_fields(select_content)

        as_pattern = re.compile(
            r"^(.+?)\s+as\s+([a-zA-Z_][a-zA-Z0-9_]*)$", re.IGNORECASE
        )
        implicit_pattern = re.compile(
            r"^([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)$", re.IGNORECASE
        )

        for field_expr in fields:
            field_expr = field_expr.strip()
            if not field_expr or field_expr.upper() == "SELECT":
                continue

            alias_name = None
            source = None
            expression = field_expr

            match = as_pattern.match(field_expr)
            if match:
                expression = match.group(1).strip()
                alias_name = match.group(2).lower()
            else:
                match = implicit_pattern.match(field_expr)
                if match:
                    potential_source = match.group(1)
                    field_name = match.group(2)
                    if potential_source.lower() in {a.lower() for a in known_aliases}:
                        alias_name = field_name.lower()
                        source = potential_source.lower()
                else:
                    field_name_match = re.match(
                        r"^([a-zA-Z_][a-zA-Z0-9_]*)$", field_expr.strip()
                    )
                    if field_name_match:
                        alias_name = field_name_match.group(1).lower()

            if alias_name:
                aliases.append(
                    {"alias": alias_name, "source": source, "expression": expression}
                )

        return aliases

    def _split_fields(self, select_content: str) -> List[str]:
        """Разбить SELECT content на поля."""
        fields = []
        depth = 0
        current = ""
        in_string = False
        string_char = None

        i = 0
        while i < len(select_content):
            char = select_content[i]

            if not in_string and char in ("'", '"'):
                in_string = True
                string_char = char
                current += char
            elif in_string and char == string_char:
                if i + 1 < len(select_content) and select_content[i + 1] == string_char:
                    current += char + char
                    i += 1
                else:
                    in_string = False
                    string_char = None
                    current += char
            elif not in_string:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                elif char == "," and depth == 0:
                    fields.append(current)
                    current = ""
                    i += 1
                    continue
                current += char

            i += 1

        if current:
            fields.append(current)

        return fields

    def extract_model_refs(self, sql_content: str) -> Dict[str, Dict[str, Any]]:
        """Извлечь ссылки на таблицы моделей (_m.*)."""
        refs = {}

        for match in self.MODEL_REF_PATTERN.finditer(sql_content):
            ref_full = match.group(0)
            path = ref_full[3:]

            parts = path.split(".")
            ref_type = "sequence" if parts[-1].lower().endswith("seq") else "table"

            refs[ref_full] = {
                "path": path,
                "parts": parts,
                "type": ref_type,
                "full_ref": ref_full,
            }

        return refs

    def extract_workflow_refs(self, sql_content: str) -> Dict[str, Dict[str, Any]]:
        """Извлечь ссылки на запросы workflow (_w.*)."""
        refs = {}

        for match in self.WORKFLOW_REF_PATTERN.finditer(sql_content):
            ref_full = match.group(0)
            path = ref_full[3:]

            parts = path.split(".")

            if len(parts) < 2:
                continue

            ref_type = "cte" if "cte" in parts else "query"

            refs[ref_full] = {
                "path": path,
                "parts": parts,
                "type": ref_type,
                "full_ref": ref_full,
            }

        return refs

    def extract_project_props(self, sql_content: str) -> Dict[str, Any]:
        """Извлечь ссылки на свойства проекта (_p.props.*)."""
        props = {}

        for match in self.PROJECT_PROP_PATTERN.finditer(sql_content):
            ref_full = match.group(0)
            prop_name = match.group(1)

            props[prop_name] = {
                "full_ref": ref_full,
                "name": prop_name,
            }

        return props

    def extract_context_flags(self, sql_content: str) -> Dict[str, Any]:
        """Извлечь ссылки на флаги контекста (_ctx.flags.*)."""
        flags = {}

        for match in self.CONTEXT_FLAG_PATTERN.finditer(sql_content):
            ref_full = match.group(0)
            flag_path = match.group(1)
            parts = flag_path.split(".")

            flags[flag_path] = {
                "full_ref": ref_full,
                "path": flag_path,
                "parts": parts,
            }

        return flags

    def extract_context_constants(self, sql_content: str) -> Dict[str, Any]:
        """Извлечь ссылки на константы контекста (_ctx.const.*)."""
        constants = {}

        for match in self.CONTEXT_CONST_PATTERN.finditer(sql_content):
            ref_full = match.group(0)
            const_name = match.group(1)

            constants[const_name] = {
                "full_ref": ref_full,
                "name": const_name,
            }

        return constants

    def parse(self, sql_content: str) -> SQLMetadata:
        """Полный парсинг SQL."""
        metadata = SQLMetadata()

        metadata.cte = self.extract_cte(sql_content)
        cte_names = set(metadata.cte.keys())

        metadata.tables = self.extract_tables(sql_content, cte_names)

        table_aliases = set()
        for table_info in metadata.tables.values():
            table_aliases.add(table_info["alias"])
        for cte_name in cte_names:
            table_aliases.add(cte_name)

        metadata.parameters = self.extract_parameters(sql_content, table_aliases)

        known_aliases = table_aliases | cte_names
        metadata.aliases = self.extract_field_aliases(sql_content, known_aliases)

        metadata.functions = self.extract_functions(sql_content)

        metadata.model_refs = self.extract_model_refs(sql_content)
        metadata.workflow_refs = self.extract_workflow_refs(sql_content)

        metadata.project_props = self.extract_project_props(sql_content)
        metadata.context_flags = self.extract_context_flags(sql_content)
        metadata.context_constants = self.extract_context_constants(sql_content)

        from FW.parsing.inline_config_parser import parse_inline_configs

        inline_result = parse_inline_configs(sql_content)
        metadata.inline_query_config = inline_result.query_config
        metadata.inline_cte_configs = inline_result.cte_configs
        metadata.inline_attr_configs = inline_result.attr_configs

        return metadata
