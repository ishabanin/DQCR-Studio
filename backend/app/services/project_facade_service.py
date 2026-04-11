from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.services.fw_service import FWService

ResolveModelIdFn = Callable[[Path, str | None], str]
BuildValidationResultFn = Callable[[Path, str, str, list[str] | None], dict[str, object]]
AttachWorkflowContextFn = Callable[[dict[str, object], Path, str], dict[str, object]]
RecordBuildResultFn = Callable[[str, dict[str, object]], None]
EnsureProjectWorkflowCacheFn = Callable[[str], dict[str, object]]
TriggerWorkflowRebuildFn = Callable[[str, list[str] | None], dict[str, object]]
ResolveModelIdFromFilePathFn = Callable[[Path, str | None], str | None]
ApplyQuickfixAddFieldFn = Callable[[Path, str, str], dict[str, object]]
ApplyQuickfixRenameFolderFn = Callable[[Path, str, str | None], dict[str, object]]
AppendValidationHistoryFn = Callable[[str, dict[str, object]], None]
GetValidationHistoryFn = Callable[[str, int], list[dict[str, object]]]
ResolveModelIdForBuildFn = Callable[[Path, str | None], str]
GetProjectBuildHistoryFn = Callable[[str], list[dict[str, object]]]
FindProjectBuildFn = Callable[[str, str], dict[str, object]]
BuildFilesTreeFn = Callable[[list[dict[str, object]]], dict[str, object]]
ResolveExistingBuildOutputDirFn = Callable[[str, str], Path]
GetSupportedBuildEnginesFn = Callable[[], set[str]]
ResolveModelPathFn = Callable[[Path, str], Path]
RenderEnginePreviewSqlFn = Callable[[str, str], str]

_FW_SERVICE: FWService | None = None
_RESOLVE_MODEL_ID_FOR_VALIDATION: ResolveModelIdFn | None = None
_BUILD_VALIDATION_RESULT: BuildValidationResultFn | None = None
_ATTACH_WORKFLOW_CONTEXT: AttachWorkflowContextFn | None = None
_RECORD_BUILD_RESULT: RecordBuildResultFn | None = None
_ENSURE_PROJECT_WORKFLOW_CACHE: EnsureProjectWorkflowCacheFn | None = None
_TRIGGER_WORKFLOW_REBUILD: TriggerWorkflowRebuildFn | None = None
_RESOLVE_MODEL_ID_FROM_FILE_PATH: ResolveModelIdFromFilePathFn | None = None
_APPLY_QUICKFIX_ADD_FIELD: ApplyQuickfixAddFieldFn | None = None
_APPLY_QUICKFIX_RENAME_FOLDER: ApplyQuickfixRenameFolderFn | None = None
_APPEND_VALIDATION_HISTORY: AppendValidationHistoryFn | None = None
_GET_VALIDATION_HISTORY: GetValidationHistoryFn | None = None
_RESOLVE_MODEL_ID_FOR_BUILD: ResolveModelIdForBuildFn | None = None
_GET_PROJECT_BUILD_HISTORY: GetProjectBuildHistoryFn | None = None
_FIND_PROJECT_BUILD: FindProjectBuildFn | None = None
_BUILD_FILES_TREE: BuildFilesTreeFn | None = None
_RESOLVE_EXISTING_BUILD_OUTPUT_DIR: ResolveExistingBuildOutputDirFn | None = None
_GET_SUPPORTED_BUILD_ENGINES: GetSupportedBuildEnginesFn | None = None
_RESOLVE_MODEL_PATH: ResolveModelPathFn | None = None
_RENDER_ENGINE_PREVIEW_SQL: RenderEnginePreviewSqlFn | None = None


def configure_project_facade(
    *,
    fw_service: FWService,
    resolve_model_id_for_validation_fn: ResolveModelIdFn,
    build_validation_result_fn: BuildValidationResultFn,
    attach_workflow_context_fn: AttachWorkflowContextFn,
    record_build_result_fn: RecordBuildResultFn,
    ensure_project_workflow_cache_fn: EnsureProjectWorkflowCacheFn,
    trigger_workflow_rebuild_fn: TriggerWorkflowRebuildFn,
    resolve_model_id_from_file_path_fn: ResolveModelIdFromFilePathFn,
    apply_quickfix_add_field_fn: ApplyQuickfixAddFieldFn,
    apply_quickfix_rename_folder_fn: ApplyQuickfixRenameFolderFn,
    append_validation_history_fn: AppendValidationHistoryFn,
    get_validation_history_fn: GetValidationHistoryFn,
    resolve_model_id_for_build_fn: ResolveModelIdForBuildFn,
    get_project_build_history_fn: GetProjectBuildHistoryFn,
    find_project_build_fn: FindProjectBuildFn,
    build_files_tree_fn: BuildFilesTreeFn,
    resolve_existing_build_output_dir_fn: ResolveExistingBuildOutputDirFn,
    get_supported_build_engines_fn: GetSupportedBuildEnginesFn,
    resolve_model_path_fn: ResolveModelPathFn,
    render_engine_preview_sql_fn: RenderEnginePreviewSqlFn,
) -> None:
    global _FW_SERVICE
    global _RESOLVE_MODEL_ID_FOR_VALIDATION
    global _BUILD_VALIDATION_RESULT
    global _ATTACH_WORKFLOW_CONTEXT
    global _RECORD_BUILD_RESULT
    global _ENSURE_PROJECT_WORKFLOW_CACHE
    global _TRIGGER_WORKFLOW_REBUILD
    global _RESOLVE_MODEL_ID_FROM_FILE_PATH
    global _APPLY_QUICKFIX_ADD_FIELD
    global _APPLY_QUICKFIX_RENAME_FOLDER
    global _APPEND_VALIDATION_HISTORY
    global _GET_VALIDATION_HISTORY
    global _RESOLVE_MODEL_ID_FOR_BUILD
    global _GET_PROJECT_BUILD_HISTORY
    global _FIND_PROJECT_BUILD
    global _BUILD_FILES_TREE
    global _RESOLVE_EXISTING_BUILD_OUTPUT_DIR
    global _GET_SUPPORTED_BUILD_ENGINES
    global _RESOLVE_MODEL_PATH
    global _RENDER_ENGINE_PREVIEW_SQL

    _FW_SERVICE = fw_service
    _RESOLVE_MODEL_ID_FOR_VALIDATION = resolve_model_id_for_validation_fn
    _BUILD_VALIDATION_RESULT = build_validation_result_fn
    _ATTACH_WORKFLOW_CONTEXT = attach_workflow_context_fn
    _RECORD_BUILD_RESULT = record_build_result_fn
    _ENSURE_PROJECT_WORKFLOW_CACHE = ensure_project_workflow_cache_fn
    _TRIGGER_WORKFLOW_REBUILD = trigger_workflow_rebuild_fn
    _RESOLVE_MODEL_ID_FROM_FILE_PATH = resolve_model_id_from_file_path_fn
    _APPLY_QUICKFIX_ADD_FIELD = apply_quickfix_add_field_fn
    _APPLY_QUICKFIX_RENAME_FOLDER = apply_quickfix_rename_folder_fn
    _APPEND_VALIDATION_HISTORY = append_validation_history_fn
    _GET_VALIDATION_HISTORY = get_validation_history_fn
    _RESOLVE_MODEL_ID_FOR_BUILD = resolve_model_id_for_build_fn
    _GET_PROJECT_BUILD_HISTORY = get_project_build_history_fn
    _FIND_PROJECT_BUILD = find_project_build_fn
    _BUILD_FILES_TREE = build_files_tree_fn
    _RESOLVE_EXISTING_BUILD_OUTPUT_DIR = resolve_existing_build_output_dir_fn
    _GET_SUPPORTED_BUILD_ENGINES = get_supported_build_engines_fn
    _RESOLVE_MODEL_PATH = resolve_model_path_fn
    _RENDER_ENGINE_PREVIEW_SQL = render_engine_preview_sql_fn


def _require(value: object, name: str) -> object:
    if value is None:
        raise RuntimeError(f"Project facade is not configured: '{name}' is missing.")
    return value


def get_fw_service() -> FWService:
    return _require(_FW_SERVICE, "fw_service")  # type: ignore[return-value]


def ensure_project_workflow_cache(project_id: str) -> dict[str, object]:
    fn = _require(_ENSURE_PROJECT_WORKFLOW_CACHE, "ensure_project_workflow_cache_fn")
    return fn(project_id)  # type: ignore[misc]


def trigger_project_workflow_rebuild(project_id: str, changed_paths: list[str] | None = None) -> dict[str, object]:
    fn = _require(_TRIGGER_WORKFLOW_REBUILD, "trigger_workflow_rebuild_fn")
    return fn(project_id, changed_paths)  # type: ignore[misc]


def resolve_model_id_for_validation(project_path: Path, explicit_model_id: str | None) -> str:
    fn = _require(_RESOLVE_MODEL_ID_FOR_VALIDATION, "resolve_model_id_for_validation_fn")
    return fn(project_path, explicit_model_id)  # type: ignore[misc]


def build_validation_result(
    project_path: Path,
    project_id: str,
    model_id: str,
    categories: list[str] | None,
) -> dict[str, object]:
    fn = _require(_BUILD_VALIDATION_RESULT, "build_validation_result_fn")
    return fn(project_path, project_id, model_id, categories)  # type: ignore[misc]


def attach_workflow_context(payload: dict[str, object], project_path: Path, model_id: str) -> dict[str, object]:
    fn = _require(_ATTACH_WORKFLOW_CONTEXT, "attach_workflow_context_fn")
    return fn(payload, project_path, model_id)  # type: ignore[misc]


def record_build_result(project_id: str, result: dict[str, object]) -> None:
    fn = _require(_RECORD_BUILD_RESULT, "record_build_result_fn")
    fn(project_id, result)  # type: ignore[misc]


def resolve_model_id_from_file_path(project_path: Path, file_path: str | None) -> str | None:
    fn = _require(_RESOLVE_MODEL_ID_FROM_FILE_PATH, "resolve_model_id_from_file_path_fn")
    return fn(project_path, file_path)  # type: ignore[misc]


def apply_quickfix_add_field(project_path: Path, model_id: str, field_name: str) -> dict[str, object]:
    fn = _require(_APPLY_QUICKFIX_ADD_FIELD, "apply_quickfix_add_field_fn")
    return fn(project_path, model_id, field_name)  # type: ignore[misc]


def apply_quickfix_rename_folder(project_path: Path, file_path: str, new_name: str | None) -> dict[str, object]:
    fn = _require(_APPLY_QUICKFIX_RENAME_FOLDER, "apply_quickfix_rename_folder_fn")
    return fn(project_path, file_path, new_name)  # type: ignore[misc]


def append_validation_history(project_id: str, result: dict[str, object]) -> None:
    fn = _require(_APPEND_VALIDATION_HISTORY, "append_validation_history_fn")
    fn(project_id, result)  # type: ignore[misc]


def get_validation_history(project_id: str, limit: int = 5) -> list[dict[str, object]]:
    fn = _require(_GET_VALIDATION_HISTORY, "get_validation_history_fn")
    return fn(project_id, limit)  # type: ignore[misc]


def resolve_model_id_for_build(project_path: Path, explicit_model_id: str | None) -> str:
    fn = _require(_RESOLVE_MODEL_ID_FOR_BUILD, "resolve_model_id_for_build_fn")
    return fn(project_path, explicit_model_id)  # type: ignore[misc]


def get_project_build_history(project_id: str) -> list[dict[str, object]]:
    fn = _require(_GET_PROJECT_BUILD_HISTORY, "get_project_build_history_fn")
    return fn(project_id)  # type: ignore[misc]


def find_project_build(project_id: str, build_id: str) -> dict[str, object]:
    fn = _require(_FIND_PROJECT_BUILD, "find_project_build_fn")
    return fn(project_id, build_id)  # type: ignore[misc]


def build_files_tree(items: list[dict[str, object]]) -> dict[str, object]:
    fn = _require(_BUILD_FILES_TREE, "build_files_tree_fn")
    return fn(items)  # type: ignore[misc]


def resolve_existing_build_output_dir(project_id: str, build_id: str) -> Path:
    fn = _require(_RESOLVE_EXISTING_BUILD_OUTPUT_DIR, "resolve_existing_build_output_dir_fn")
    return fn(project_id, build_id)  # type: ignore[misc]


def get_supported_build_engines() -> set[str]:
    fn = _require(_GET_SUPPORTED_BUILD_ENGINES, "get_supported_build_engines_fn")
    return fn()  # type: ignore[misc]


def resolve_model_path(project_path: Path, model_id: str) -> Path:
    fn = _require(_RESOLVE_MODEL_PATH, "resolve_model_path_fn")
    return fn(project_path, model_id)  # type: ignore[misc]


def render_engine_preview_sql(raw_sql: str, engine: str) -> str:
    fn = _require(_RENDER_ENGINE_PREVIEW_SQL, "render_engine_preview_sql_fn")
    return fn(raw_sql, engine)  # type: ignore[misc]
