from __future__ import annotations

from copy import deepcopy
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, status

router = APIRouter(prefix="/admin", tags=["admin"])

TemplateName = Literal["flx", "dwh_mart", "dq_control"]

_TEMPLATES: dict[str, dict[str, object]] = {
    "flx": {
        "name": "flx",
        "content": "name: flx\nengine: dqcr\nrules:\n  folders:\n    - name: 01_stage\n      materialized: insert_fc\n      enabled: true\n",
        "rules": {
            "folders": [
                {"name": "01_stage", "materialized": "insert_fc", "enabled": True},
            ]
        },
    },
    "dwh_mart": {
        "name": "dwh_mart",
        "content": "name: dwh_mart\nengine: dqcr\nrules:\n  folders:\n    - name: 01_load\n      materialized: stage_calcid\n      enabled: true\n",
        "rules": {
            "folders": [
                {"name": "01_load", "materialized": "stage_calcid", "enabled": True},
            ]
        },
    },
    "dq_control": {
        "name": "dq_control",
        "content": "name: dq_control\nengine: dqcr\nrules:\n  folders:\n    - name: 01_checks\n      materialized: insert_fc\n      enabled: true\n",
        "rules": {
            "folders": [
                {"name": "01_checks", "materialized": "insert_fc", "enabled": True},
            ]
        },
    },
}

_RULES: list[dict[str, object]] = [
    {
        "id": "sql.non_empty",
        "name": "SQL non-empty",
        "severity": "error",
        "enabled": True,
        "pattern": "select|insert|update|delete",
        "description": "SQL file must contain a DML statement.",
    },
    {
        "id": "descriptions.comment_present",
        "name": "SQL comments present",
        "severity": "warning",
        "enabled": True,
        "pattern": "--",
        "description": "SQL should include at least one comment.",
    },
]

_MACROS: list[dict[str, str]] = [
    {"name": "ref", "source": "builtin", "description": "Resolve model/table reference."},
    {"name": "source", "source": "builtin", "description": "Resolve external source."},
    {"name": "var", "source": "builtin", "description": "Resolve variable value."},
    {"name": "env_var", "source": "builtin", "description": "Resolve environment variable."},
    {"name": "config", "source": "builtin", "description": "Apply inline SQL config."},
]


def _require_template(name: str) -> dict[str, object]:
    template = _TEMPLATES.get(name)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template '{name}' not found.")
    return template


@router.get("/templates")
def list_templates() -> list[dict[str, str]]:
    return [{"name": key} for key in sorted(_TEMPLATES.keys())]


@router.get("/templates/{name}")
def get_template(name: str) -> dict[str, object]:
    template = _require_template(name)
    return deepcopy(template)


@router.put("/templates/{name}")
def put_template(name: str, payload: dict[str, object] = Body(...)) -> dict[str, object]:
    template = _require_template(name)
    content = payload.get("content")
    rules = payload.get("rules")

    if isinstance(content, str):
        template["content"] = content
    if isinstance(rules, dict):
        folders = rules.get("folders")
        if isinstance(folders, list):
            safe_folders: list[dict[str, object]] = []
            for item in folders:
                if not isinstance(item, dict):
                    continue
                folder_name = str(item.get("name", "")).strip()
                if not folder_name:
                    continue
                safe_folders.append(
                    {
                        "name": folder_name,
                        "materialized": str(item.get("materialized", "insert_fc")),
                        "enabled": bool(item.get("enabled", True)),
                    }
                )
            template["rules"] = {"folders": safe_folders}

    return deepcopy(template)


@router.get("/rules")
def get_rules() -> dict[str, list[dict[str, object]]]:
    return {"rules": deepcopy(_RULES)}


@router.put("/rules")
def put_rules(payload: dict[str, object] = Body(...)) -> dict[str, list[dict[str, object]]]:
    rules_raw = payload.get("rules")
    if not isinstance(rules_raw, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'rules' must be a list.")

    next_rules: list[dict[str, object]] = []
    for item in rules_raw:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("id", "")).strip()
        if not rule_id:
            continue
        severity = str(item.get("severity", "warning")).strip().lower()
        if severity not in {"pass", "warning", "error"}:
            severity = "warning"
        next_rules.append(
            {
                "id": rule_id,
                "name": str(item.get("name", rule_id)),
                "severity": severity,
                "enabled": bool(item.get("enabled", True)),
                "pattern": str(item.get("pattern", "")),
                "description": str(item.get("description", "")),
            }
        )

    _RULES.clear()
    _RULES.extend(next_rules)
    return {"rules": deepcopy(_RULES)}


@router.get("/macros")
def get_macros() -> dict[str, list[dict[str, str]]]:
    return {"macros": deepcopy(_MACROS)}
