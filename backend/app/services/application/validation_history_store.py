from __future__ import annotations

VALIDATION_HISTORY: dict[str, list[dict[str, object]]] = {}


def append_validation_history(project_id: str, result: dict[str, object], max_items: int = 20) -> None:
    history = VALIDATION_HISTORY.setdefault(project_id, [])
    history.insert(0, result)
    VALIDATION_HISTORY[project_id] = history[:max_items]


def get_validation_history(project_id: str, limit: int = 5) -> list[dict[str, object]]:
    safe_limit = max(1, int(limit))
    return VALIDATION_HISTORY.get(project_id, [])[:safe_limit]
