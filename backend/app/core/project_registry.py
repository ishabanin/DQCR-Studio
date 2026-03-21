from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, NotRequired, TypedDict


RegistrySourceType = Literal["internal", "imported", "linked"]
RegistryAvailability = Literal["available", "unavailable"]


class ProjectRegistryEntry(TypedDict):
    id: str
    name: str
    source_type: RegistrySourceType
    source_path: str | None
    availability_status: RegistryAvailability
    description: NotRequired[str]
    visibility: NotRequired[Literal["public", "private"]]
    tags: NotRequired[list[str]]


REGISTRY_FILE_NAME = ".dqcr_projects_registry.json"


def registry_file_path(base_projects_path: Path) -> Path:
    return base_projects_path / REGISTRY_FILE_NAME


def load_registry(base_projects_path: Path) -> dict[str, ProjectRegistryEntry]:
    registry_path = registry_file_path(base_projects_path)
    if not registry_path.exists() or not registry_path.is_file():
        return {}

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if not isinstance(raw, dict):
        return {}

    entries: dict[str, ProjectRegistryEntry] = {}
    for project_id, item in raw.items():
        if not isinstance(project_id, str) or not isinstance(item, dict):
            continue
        source_type = item.get("source_type")
        if source_type not in {"internal", "imported", "linked"}:
            continue
        name = str(item.get("name", project_id)).strip() or project_id
        source_path_raw = item.get("source_path")
        source_path = str(source_path_raw).strip() if isinstance(source_path_raw, str) and source_path_raw.strip() else None
        availability_status = item.get("availability_status")
        status: RegistryAvailability = "available" if availability_status == "available" else "unavailable"
        entries[project_id] = {
            "id": project_id,
            "name": name,
            "source_type": source_type,
            "source_path": source_path,
            "availability_status": status,
        }
        description_raw = item.get("description")
        if isinstance(description_raw, str):
            entries[project_id]["description"] = description_raw

        visibility_raw = item.get("visibility")
        if visibility_raw in {"public", "private"}:
            entries[project_id]["visibility"] = visibility_raw

        tags_raw = item.get("tags")
        if isinstance(tags_raw, list):
            entries[project_id]["tags"] = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
    return entries


def save_registry(base_projects_path: Path, entries: dict[str, ProjectRegistryEntry]) -> None:
    base_projects_path.mkdir(parents=True, exist_ok=True)
    serialized = {
        key: {
            "name": item["name"],
            "source_type": item["source_type"],
            "source_path": item["source_path"],
            "availability_status": item["availability_status"],
            "description": item.get("description", ""),
            "visibility": item.get("visibility", "private"),
            "tags": item.get("tags", []),
        }
        for key, item in sorted(entries.items(), key=lambda pair: pair[0].lower())
    }
    registry_path = registry_file_path(base_projects_path)
    registry_path.write_text(json.dumps(serialized, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def get_registry_entry(base_projects_path: Path, project_id: str) -> ProjectRegistryEntry | None:
    return load_registry(base_projects_path).get(project_id)


def upsert_registry_entry(base_projects_path: Path, entry: ProjectRegistryEntry) -> None:
    entries = load_registry(base_projects_path)
    entries[entry["id"]] = entry
    save_registry(base_projects_path, entries)


def derive_link_availability(source_path: str | None) -> RegistryAvailability:
    if not source_path:
        return "unavailable"
    path_obj = Path(source_path)
    return "available" if path_obj.exists() and path_obj.is_dir() else "unavailable"
