"""Inline configuration parser for SQL files."""
import re
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from FW.logging_config import get_logger

logger = get_logger("inline_config_parser")


@dataclass
class InlineConfigBlock:
    """Блок inline конфига с позицией в SQL."""
    content: str
    start_pos: int
    end_pos: int
    config_type: str  # 'query', 'cte', 'attribute'


def _find_config_blocks(sql_content: str) -> List[InlineConfigBlock]:
    """Найти все блоки @config(...) в SQL с балансированием скобок."""
    blocks = []
    
    pattern = re.compile(r'/\*\s*@config\s*\(', re.DOTALL)
    
    for match in pattern.finditer(sql_content):
        start_paren = match.end() - 1
        depth = 1
        pos = start_paren + 1
        
        while pos < len(sql_content) and depth > 0:
            if sql_content[pos] == '(':
                depth += 1
            elif sql_content[pos] == ')':
                depth -= 1
            pos += 1
        
        if depth == 0:
            end_paren = pos - 1
            content_start = start_paren + 1
            content_end = end_paren
            
            content = sql_content[content_start:content_end]
            
            blocks.append(InlineConfigBlock(
                content=content,
                start_pos=match.start(),
                end_pos=pos,
                config_type='unknown'
            ))
    
    return blocks


CONFIG_BLOCK_PATTERN = re.compile(
    r'/\*\s*@config\s*\(\s*(\s*.*?)\s*\)\s*\*/',
    re.DOTALL
)


@dataclass
class InlineConfigResult:
    """Результат парсинга inline конфигов из SQL."""
    query_config: Optional[Dict[str, Any]] = None
    cte_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    attr_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)


def _parse_yaml_content(yaml_str: str) -> Optional[Dict[str, Any]]:
    """Парсить YAML содержимое из @config(...)."""
    try:
        lines = yaml_str.split('\n')
        if not lines:
            return {}
        
        min_indent = float('inf')
        for line in lines[1:]:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            min_indent = 0
        
        indented_lines = []
        for i, line in enumerate(lines):
            if line.strip():
                if i == 0:
                    indented_lines.append('  ' + line)
                else:
                    current_indent = len(line) - len(line.lstrip())
                    adjusted = line[min_indent:] if len(line) >= min_indent else line
                    indented_lines.append('  ' + adjusted)
            else:
                indented_lines.append(line)
        
        indented_yaml = '\n'.join(indented_lines)
        
        result = yaml.safe_load(indented_yaml)
        if result is None:
            return {}
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse inline config YAML: {e}")
        return None


def _find_cte_boundaries(sql_content: str) -> List[Tuple[str, int, int]]:
    """Найти границы всех CTE (имя, start_pos, end_pos).
    
    Returns:
        Список кортежей (cte_name, start_of_as_paren, end_of_paren)
    """
    ctes = []
    
    cte_def_pattern = re.compile(
        r'\b([a-zA-Z0-9_]+)\s+as\s*\(',
        re.IGNORECASE
    )
    
    for match in cte_def_pattern.finditer(sql_content):
        cte_name = match.group(1)
        as_paren_start = match.end() - 1  # Позиция '('
        
        depth = 1
        pos = as_paren_start + 1
        while pos < len(sql_content) and depth > 0:
            if sql_content[pos] == '(':
                depth += 1
            elif sql_content[pos] == ')':
                depth -= 1
            pos += 1
        
        if depth == 0:
            ctes.append((cte_name, as_paren_start, pos - 1))
    
    return ctes


def _find_select_from_positions(sql_content: str) -> Tuple[Optional[int], Optional[int]]:
    """Найти позиции SELECT и FROM в основном запросе."""
    select_match = re.search(r'\bSELECT\s+', sql_content, re.IGNORECASE)
    from_match = re.search(r'\bFROM\b', sql_content, re.IGNORECASE)
    
    select_pos = select_match.start() if select_match else None
    from_pos = from_match.start() if from_match else None
    
    return select_pos, from_pos


def _find_with_clause_position(sql_content: str) -> Optional[int]:
    """Найти позицию начала WITH clause."""
    with_match = re.search(r'\bWITH\s+', sql_content, re.IGNORECASE)
    return with_match.start() if with_match else None


def _find_cte_for_position(pos: int, cte_boundaries: List[Tuple[str, int, int]]) -> Optional[str]:
    """Найти CTE, внутри которого находится позиция."""
    for cte_name, start, end in cte_boundaries:
        if start < pos < end:
            return cte_name
    return None


def _determine_block_type(block: InlineConfigBlock, sql_content: str) -> str:
    """Определить тип конфига по позиции в SQL."""
    block_center = (block.start_pos + block.end_pos) // 2
    
    with_pos = _find_with_clause_position(sql_content)
    select_pos, from_pos = _find_select_from_positions(sql_content)
    cte_boundaries = _find_cte_boundaries(sql_content)
    
    if with_pos is not None and block.start_pos < with_pos:
        return 'query'
    
    if select_pos is not None and from_pos is not None:
        if select_pos < block_center < from_pos:
            cte_name = _find_cte_for_position(block_center, cte_boundaries)
            if cte_name:
                return 'cte'
            return 'attribute'
    
    if cte_boundaries:
        cte_name = _find_cte_for_position(block_center, cte_boundaries)
        if cte_name:
            return 'cte'
    
    return 'query'


def _find_attribute_alias_for_config(sql_content: str, config_start_pos: int) -> Optional[str]:
    """Найти alias атрибута, к которому относится блок конфига.
    
    Логика:
    1. Ищем alias ПЕРЕД блоком конфига (AS alias) - это приоритет
    2. Если не найден, ищем колонку ПОСЛЕ конфига (таблица.колонка или просто колонка)
    """
    before_config = sql_content[:config_start_pos]
    
    # Ищем alias перед конфигом
    matches = list(re.finditer(r'\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)', before_config, re.IGNORECASE))
    if matches:
        alias = matches[-1].group(1).strip()
        alias = alias.rstrip(',')
        return alias
    
    # Ищем column перед конфигом (таблица.колонка)
    dot_matches = list(re.finditer(r'\.([a-zA-Z_][a-zA-Z0-9_]*)\s*$', before_config, re.IGNORECASE))
    if dot_matches:
        alias = dot_matches[-1].group(1).strip()
        alias = alias.rstrip(',')
        return alias
    
    # Конфиг в начале SELECT - ищем колонку ПОСЛЕ конфига (это правильный атрибут!)
    after_config = sql_content[config_start_pos:]
    
    # Ищем колонку после конфига (таблица.колонка или просто колонка перед запятой или переносом строки)
    col_match = re.search(r'(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)\s*[,)\n]', after_config, re.IGNORECASE)
    if col_match:
        alias = col_match.group(1).strip()
        return alias
    
    return None


def _extract_cte_names_from_sql(sql_content: str) -> Dict[int, str]:
    """Извлечь все CTE имена с их позициями в SQL."""
    cte_names = {}
    
    cte_def_pattern = re.compile(
        r'\b([a-zA-Z0-9_]+)\s+as\s*\(',
        re.IGNORECASE
    )
    
    for match in cte_def_pattern.finditer(sql_content):
        cte_names[match.start()] = match.group(1)
    
    return cte_names


def _find_cte_for_cte_config(block: InlineConfigBlock, sql_content: str) -> str:
    """Найти имя CTE для блока конфига внутри CTE."""
    cte_names = _extract_cte_names_from_sql(sql_content)
    
    closest_cte_start = None
    closest_cte_name = None
    
    for cte_pos, cte_name in cte_names.items():
        if cte_pos < block.start_pos:
            if closest_cte_start is None or cte_pos > closest_cte_start:
                closest_cte_start = cte_pos
                closest_cte_name = cte_name
    
    return closest_cte_name if closest_cte_name else 'unknown'


def parse_inline_configs(sql_content: str) -> InlineConfigResult:
    """Парсить inline конфиги из SQL файла.
    
    Args:
        sql_content: Содержимое SQL файла
        
    Returns:
        InlineConfigResult с распарсенными конфигами
    """
    result = InlineConfigResult()
    
    blocks = _find_config_blocks(sql_content)
    
    if not blocks:
        return result
    
    cte_boundaries = _find_cte_boundaries(sql_content)
    
    for block in blocks:
        config_type = _determine_block_type(block, sql_content)
        block.config_type = config_type
        
        config_data = _parse_yaml_content(block.content)
        
        if config_data is None:
            continue
        
        if config_type == 'query':
            result.query_config = config_data
            
        elif config_type == 'cte':
            cte_name = _find_cte_for_cte_config(block, sql_content)
            result.cte_configs[cte_name] = config_data
            
        elif config_type == 'attribute':
            alias = _find_attribute_alias_for_config(sql_content, block.start_pos)
            if alias:
                result.attr_configs[alias.lower()] = config_data
    
    return result


def remove_inline_configs(sql_content: str) -> str:
    """Удалить все блоки @config(...) из SQL.
    
    Args:
        sql_content: SQL с блоками @config
        
    Returns:
        SQL без блоков @config
    """
    return CONFIG_BLOCK_PATTERN.sub('', sql_content)


def has_inline_configs(sql_content: str) -> bool:
    """Проверить есть ли inline конфиги в SQL."""
    return CONFIG_BLOCK_PATTERN.search(sql_content) is not None
