"""Pattern matcher - сопоставление масок с * и ?."""
import re
from typing import Dict, Optional, Any


def pattern_to_regex(pattern: str) -> re.Pattern:
    """Преобразовать маску в регулярное выражение.
    
    Синтаксис масок:
    - * - любое количество символов
    - ? - ровно один символ
    
    Args:
        pattern: маска (например, "001_*_vtb")
        
    Returns:
        Скомпилированное регулярное выражение
    """
    regex_str = pattern
    regex_str = regex_str.replace('.', r'\.')
    regex_str = regex_str.replace('*', '.*')
    regex_str = regex_str.replace('?', '.')
    regex_str = f'^{regex_str}$'
    return re.compile(regex_str, re.IGNORECASE)


def match_pattern(text: str, pattern: str) -> bool:
    """Проверить, соответствует ли текст маске.
    
    Args:
        text: текст для проверки
        pattern: маска
        
    Returns:
        True если соответствует
    """
    if not text or not pattern:
        return False
    
    try:
        regex = pattern_to_regex(pattern)
        return regex.match(text) is not None
    except re.error:
        return False


def match_any_pattern(text: str, patterns: list) -> bool:
    """Проверить, соответствует ли текст любой из масок.
    
    Args:
        text: текст для проверки
        patterns: список масок
        
    Returns:
        True если соответствует любой маске
    """
    for pattern in patterns:
        if match_pattern(text, pattern):
            return True
    return False


def find_matching_rule(name: str, rules: Dict[str, Any]) -> Optional[Any]:
    """Найти первое подходящее правило для имени.
    
    Правила проверяются в порядке:
    1. Точное совпадение
    2. По маскам (более длинные маски имеют больший приоритет)
    
    Args:
        name: имя объекта (папки, запроса, параметра)
        rules: словарь правил {pattern: rule_definition}
        
    Returns:
        Подходящее правило или None
    """
    if not rules:
        return None
    
    if name in rules:
        return rules[name]
    
    matches = []
    for pattern, rule in rules.items():
        if match_pattern(name, pattern):
            matches.append((pattern, rule))
    
    if not matches:
        return None
    
    matches.sort(key=lambda x: len(x[0]), reverse=True)
    
    return matches[0][1]


def find_matching_rules(name: str, rules: Dict[str, Any]) -> list:
    """Найти все подходящие правила для имени.
    
    Args:
        name: имя объекта
        rules: словарь правил
        
    Returns:
        Список подходящих правил (от наиболее специфичного к менее)
    """
    if not rules:
        return []
    
    matches = []
    for pattern, rule in rules.items():
        if match_pattern(name, pattern):
            matches.append((pattern, rule))
    
    matches.sort(key=lambda x: len(x[0]), reverse=True)
    
    return [m[1] for m in matches]
