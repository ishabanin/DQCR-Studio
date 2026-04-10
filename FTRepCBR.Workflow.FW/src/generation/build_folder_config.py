"""Folder Config Builder - собирает effective config для папок во всех контекстах."""

import fnmatch
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING

from FW.models.sql_object import ConfigValue
from FW.models.configs import FolderConfig, CTEMaterializationConfig
from FW.models.enabled import evaluate_condition

if TYPE_CHECKING:
    from FW.models.project_template import RuleDefinition


def build_folder_config(
    folder: str,
    folder_path: Path,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    all_contexts: List[str],
    default_materialization: Optional[str],
    get_parent_folder_config: Optional[
        Callable[[str], Optional["FolderConfig"]]
    ] = None,
    template_name: Optional[str] = None,
    folder_rules: Optional[Dict[str, "RuleDefinition"]] = None,
    context_flags: Optional[Dict[str, Dict[str, Any]]] = None,
    context_constants: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Собрать effective config для всех контекстов папки.

    Args:
        folder: имя папки (например, "001_Load__distr")
        folder_path: полный путь к папке с SQL файлами
        folder_config: конфиг из folder.yml (текущей папки)
        workflow_config: конфиг из model.yml (workflow.folders[folder_name])
        all_contexts: все контексты проекта ["default", "vtb"]
        default_materialization: дефолтная материализация из шаблона
        get_parent_folder_config: функция для поиска конфига в родительской папке
        template_name: имя шаблона для заполнения source=template file
        folder_rules: правила для папок из шаблона {pattern: RuleDefinition}

    Returns:
        {
            "default": {
                "enabled": ConfigValue(...),
                "materialized": ConfigValue(...),
                "description": ConfigValue(...),
                "pre": [...],
                "post": [...],
                "cte": {...}
            },
            "vtb": {
                "enabled": ConfigValue(value=False, source="folder", file="...", reason="not in enabled.contexts")
            }
        }
    """
    config: Dict[str, Dict[str, Any]] = {}

    active_contexts, not_active_info = _get_active_contexts_with_info(
        folder_config=folder_config,
        workflow_config=workflow_config,
        all_contexts=all_contexts,
        get_parent_folder_config=get_parent_folder_config,
        folder=folder,
        context_flags=context_flags,
        context_constants=context_constants,
    )

    for ctx in all_contexts:
        ctx_key = ctx if ctx else "default"

        if ctx not in active_contexts:
            info = not_active_info.get(ctx, {})
            source = info.get("source", "default")
            file = info.get("file")
            reason = info.get("reason", "not applicable")
            conditions = info.get("conditions")

            config[ctx_key] = {
                "enabled": ConfigValue(
                    value=False,
                    source=source,
                    file=file,
                    reason=reason,
                    conditions=conditions,
                ),
            }
            continue

        config[ctx_key] = {}

        config[ctx_key]["enabled"] = _get_enabled_config(
            folder=folder,
            folder_config=folder_config,
            workflow_config=workflow_config,
            context=ctx,
            folder_path=folder_path,
        )

        config[ctx_key]["materialized"] = _get_materialization_config(
            folder=folder,
            folder_config=folder_config,
            workflow_config=workflow_config,
            context=ctx,
            folder_path=folder_path,
            default_materialization=default_materialization,
            template_name=template_name,
            folder_rules=folder_rules,
        )

        config[ctx_key]["description"] = _get_description_config(
            folder=folder,
            folder_config=folder_config,
            workflow_config=workflow_config,
            folder_path=folder_path,
        )

        config[ctx_key]["pre"] = _get_pre_config(
            folder=folder,
            folder_config=folder_config,
            workflow_config=workflow_config,
            folder_path=folder_path,
            template_name=template_name,
            folder_rules=folder_rules,
        )

        config[ctx_key]["post"] = _get_post_config(
            folder=folder,
            folder_config=folder_config,
            workflow_config=workflow_config,
            folder_path=folder_path,
            template_name=template_name,
            folder_rules=folder_rules,
        )

        config[ctx_key]["cte"] = _get_cte_config(
            folder=folder,
            folder_config=folder_config,
            workflow_config=workflow_config,
            context=ctx,
            folder_path=folder_path,
        )

    return config


def _get_active_contexts_with_info(
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    all_contexts: List[str],
    get_parent_folder_config: Optional[
        Callable[[str], Optional["FolderConfig"]]
    ] = None,
    folder: str = "",
    context_flags: Optional[Dict[str, Dict[str, Any]]] = None,
    context_constants: Optional[Dict[str, Dict[str, Any]]] = None,
) -> tuple[set[str], Dict[str, Dict[str, Any]]]:
    """Определить активные и неактивные контексты для папки с учетом иерархии.

    Returns:
        (active_contexts, not_active_info)
    """
    active_contexts: set[str] = set()
    not_active_info: Dict[str, Dict[str, Any]] = {}
    context_flags = context_flags or {}
    context_constants = context_constants or {}

    folder_yml_path = str(Path(folder) / "folder.yml") if folder else "folder.yml"

    current_config = folder_config
    current_folder = folder

    while current_config is None and get_parent_folder_config is not None:
        if current_folder == "" or current_folder is None:
            break
        parent_parts = current_folder.rsplit("/", 1)
        parent_folder = parent_parts[0] if len(parent_parts) > 1 else ""
        current_config = get_parent_folder_config(parent_folder)
        current_folder = parent_folder

    enabled_source = None
    enabled_file = None

    if current_config and current_config.enabled:
        cfg_contexts = current_config.enabled.contexts
        cfg_conditions = current_config.enabled.conditions
        enabled_source = "folder"
        enabled_file = folder_yml_path
        
        if cfg_conditions:
            for ctx in all_contexts:
                ctx_flags = context_flags.get(ctx, {})
                ctx_consts = context_constants.get(ctx, {})
                is_satisfied, _ = evaluate_condition(cfg_conditions, ctx_flags, ctx_consts)
                
                if cfg_contexts is None:
                    if is_satisfied:
                        active_contexts.add(ctx)
                    else:
                        not_active_info[ctx] = {
                            "source": enabled_source,
                            "file": enabled_file,
                            "reason": "condition not satisfied",
                            "conditions": cfg_conditions,
                        }
                elif ctx in cfg_contexts:
                    if is_satisfied:
                        active_contexts.add(ctx)
                    else:
                        not_active_info[ctx] = {
                            "source": enabled_source,
                            "file": enabled_file,
                            "reason": "condition not satisfied",
                            "conditions": cfg_conditions,
                        }
                else:
                    not_active_info[ctx] = {
                        "source": enabled_source,
                        "file": enabled_file,
                        "reason": "not in enabled.contexts",
                        "conditions": cfg_conditions,
                    }
        elif cfg_contexts is None:
            return set(all_contexts), {}
        else:
            for ctx in all_contexts:
                if ctx in cfg_contexts:
                    active_contexts.add(ctx)
                else:
                    not_active_info[ctx] = {
                        "source": enabled_source,
                        "file": enabled_file,
                        "reason": "not in enabled.contexts",
                        "conditions": None,
                    }
    elif workflow_config and workflow_config.enabled:
        cfg_contexts = workflow_config.enabled.contexts
        cfg_conditions = workflow_config.enabled.conditions
        enabled_source = "model"
        enabled_file = "model.yml"
        
        if cfg_conditions:
            for ctx in all_contexts:
                ctx_flags = context_flags.get(ctx, {})
                ctx_consts = context_constants.get(ctx, {})
                is_satisfied, _ = evaluate_condition(cfg_conditions, ctx_flags, ctx_consts)
                
                if cfg_contexts is None:
                    if is_satisfied:
                        active_contexts.add(ctx)
                    else:
                        not_active_info[ctx] = {
                            "source": enabled_source,
                            "file": enabled_file,
                            "reason": "condition not satisfied",
                            "conditions": cfg_conditions,
                        }
                elif ctx in cfg_contexts:
                    if is_satisfied:
                        active_contexts.add(ctx)
                    else:
                        not_active_info[ctx] = {
                            "source": enabled_source,
                            "file": enabled_file,
                            "reason": "condition not satisfied",
                            "conditions": cfg_conditions,
                        }
                else:
                    not_active_info[ctx] = {
                        "source": enabled_source,
                        "file": enabled_file,
                        "reason": "not in enabled.contexts",
                        "conditions": cfg_conditions,
                    }
        elif cfg_contexts is None:
            return set(all_contexts), {}
        else:
            for ctx in all_contexts:
                if ctx in cfg_contexts:
                    active_contexts.add(ctx)
                else:
                    not_active_info[ctx] = {
                        "source": enabled_source,
                        "file": enabled_file,
                        "reason": "not in enabled.contexts",
                        "conditions": None,
                    }
    else:
        return set(all_contexts), {}

    return active_contexts, not_active_info


def _get_enabled_config(
    folder: str,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    context: str,
    folder_path: Path,
) -> ConfigValue:
    """Определить enabled для контекста."""
    folder_yml_path = str(folder_path / "folder.yml")

    if folder_config and folder_config.enabled:
        contexts = folder_config.enabled.contexts
        if contexts is None:
            return ConfigValue(value=True, source="folder", file=folder_yml_path)
        if context in contexts:
            return ConfigValue(value=True, source="folder", file=folder_yml_path)
        return ConfigValue(value=False, source="folder", file=folder_yml_path)

    if workflow_config and workflow_config.enabled:
        contexts = workflow_config.enabled.contexts
        if contexts is None:
            return ConfigValue(value=True, source="model", file="model.yml")
        if context in contexts:
            return ConfigValue(value=True, source="model", file="model.yml")
        return ConfigValue(value=False, source="model", file="model.yml")

    return ConfigValue(value=True, source="default", file=None)


def _get_materialization_config(
    folder: str,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    context: str,
    folder_path: Path,
    default_materialization: Optional[str],
    template_name: Optional[str] = None,
    folder_rules: Optional[Dict[str, "RuleDefinition"]] = None,
) -> ConfigValue:
    """Определить materialized для контекста."""
    folder_yml_path = str(folder_path / "folder.yml")

    if folder_config and folder_config.materialized:
        return ConfigValue(
            value=folder_config.materialized, source="folder", file=folder_yml_path
        )

    if workflow_config and workflow_config.materialized:
        return ConfigValue(
            value=workflow_config.materialized, source="model", file="model.yml"
        )

    if folder_rules and folder:
        for pattern, rule in folder_rules.items():
            if fnmatch.fnmatch(folder, pattern) and rule.materialized:
                return ConfigValue(
                    value=rule.materialized, source="template_rule", file=template_name
                )

    if default_materialization:
        return ConfigValue(
            value=default_materialization, source="template", file=template_name
        )

    return ConfigValue(value=None, source="default", file=None)


def _get_description_config(
    folder: str,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    folder_path: Path,
) -> ConfigValue:
    """Определить description для папки."""
    folder_yml_path = str(folder_path / "folder.yml")

    if folder_config and folder_config.description:
        return ConfigValue(
            value=folder_config.description, source="folder", file=folder_yml_path
        )

    if workflow_config and workflow_config.description:
        return ConfigValue(
            value=workflow_config.description, source="model", file="model.yml"
        )

    return ConfigValue(value="", source="default", file=None)


def _get_pre_config(
    folder: str,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    folder_path: Path,
    template_name: Optional[str] = None,
    folder_rules: Optional[Dict[str, "RuleDefinition"]] = None,
) -> List[ConfigValue]:
    """Определить pre макросы для папки."""
    folder_yml_path = str(folder_path / "folder.yml")

    if folder_config and folder_config.pre:
        return [
            ConfigValue(value=v, source="folder", file=folder_yml_path)
            for v in folder_config.pre
        ]

    if workflow_config and workflow_config.pre:
        return [
            ConfigValue(value=v, source="model", file="model.yml")
            for v in workflow_config.pre
        ]

    if folder_rules and folder:
        for pattern, rule in folder_rules.items():
            if fnmatch.fnmatch(folder, pattern) and rule.pre:
                return [
                    ConfigValue(value=v, source="template_rule", file=template_name)
                    for v in rule.pre
                ]

    return []


def _get_post_config(
    folder: str,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    folder_path: Path,
    template_name: Optional[str] = None,
    folder_rules: Optional[Dict[str, "RuleDefinition"]] = None,
) -> List[ConfigValue]:
    """Определить post макросы для папки."""
    folder_yml_path = str(folder_path / "folder.yml")

    if folder_config and folder_config.post:
        return [
            ConfigValue(value=v, source="folder", file=folder_yml_path)
            for v in folder_config.post
        ]

    if workflow_config and workflow_config.post:
        return [
            ConfigValue(value=v, source="model", file="model.yml")
            for v in workflow_config.post
        ]

    if folder_rules and folder:
        for pattern, rule in folder_rules.items():
            if fnmatch.fnmatch(folder, pattern) and rule.post:
                return [
                    ConfigValue(value=v, source="template_rule", file=template_name)
                    for v in rule.post
                ]

    return []


def _build_folder_cte_mat_config(
    cte_name: str,
    folder_cte_config: Optional[CTEMaterializationConfig],
    workflow_cte_config: Optional[CTEMaterializationConfig],
    folder_source: str,
    folder_file: str,
    model_source: str,
    model_file: str,
) -> Dict[str, Any]:
    """Построить вложенную структуру cte_materialization для CTE на уровне папки.

    Каскадное слияние: folder -> workflow -> inline (inline имеет высший приоритет).
    """
    result = {
        "default": {"value": None, "source": "default", "file": None},
        "by_context": {},
        "by_tool": {},
    }

    def set_entry(
        target: Dict[str, Any], value: Optional[str], source: str, file: Optional[str]
    ) -> None:
        if value is not None:
            target["value"] = value
            target["source"] = source
            target["file"] = file

    folder_cte_q = None
    workflow_cte_q = None

    if folder_cte_config and folder_cte_config.cte_queries:
        folder_cte_q = folder_cte_config.cte_queries.get(cte_name)

    if workflow_cte_config and workflow_cte_config.cte_queries:
        workflow_cte_q = workflow_cte_config.cte_queries.get(cte_name)

    folder_mat = None
    folder_by_context = {}
    folder_by_tool = {}

    if folder_cte_q:
        folder_mat = folder_cte_q.cte_materialization
        folder_by_context = folder_cte_q.by_context or {}
        folder_by_tool = folder_cte_q.by_tool or {}
    elif folder_cte_config:
        folder_mat = folder_cte_config.cte_materialization
        folder_by_context = folder_cte_config.by_context or {}
        folder_by_tool = folder_cte_config.by_tool or {}

    if folder_mat is not None:
        set_entry(result["default"], folder_mat, folder_source, folder_file)
    for ctx, val in folder_by_context.items():
        result["by_context"][ctx] = {
            "value": val,
            "source": folder_source,
            "file": folder_file,
        }
    for tool, val in folder_by_tool.items():
        result["by_tool"][tool] = {
            "value": val,
            "source": folder_source,
            "file": folder_file,
        }

    if workflow_cte_q:
        wf_mat = workflow_cte_q.cte_materialization
        wf_by_context = workflow_cte_q.by_context or {}
        wf_by_tool = workflow_cte_q.by_tool or {}

        if wf_mat is not None:
            set_entry(result["default"], wf_mat, model_source, model_file)
        for ctx, val in wf_by_context.items():
            result["by_context"][ctx] = {
                "value": val,
                "source": model_source,
                "file": model_file,
            }
        for tool, val in wf_by_tool.items():
            result["by_tool"][tool] = {
                "value": val,
                "source": model_source,
                "file": model_file,
            }
    elif workflow_cte_config:
        wf_mat = workflow_cte_config.cte_materialization
        wf_by_context = workflow_cte_config.by_context or {}
        wf_by_tool = workflow_cte_config.by_tool or {}

        if wf_mat is not None and result["default"].get("value") is None:
            set_entry(result["default"], wf_mat, model_source, model_file)
        for ctx, val in wf_by_context.items():
            if ctx not in result["by_context"]:
                result["by_context"][ctx] = {
                    "value": val,
                    "source": model_source,
                    "file": model_file,
                }
        for tool, val in wf_by_tool.items():
            if tool not in result["by_tool"]:
                result["by_tool"][tool] = {
                    "value": val,
                    "source": model_source,
                    "file": model_file,
                }

    return result


def _build_folder_cte_attributes(
    cte_name: str,
    folder_cte_config: Optional[CTEMaterializationConfig],
    workflow_cte_config: Optional[CTEMaterializationConfig],
    folder_source: str,
    folder_file: str,
    model_source: str,
    model_file: str,
) -> List[Dict[str, Any]]:
    """Построить список атрибутов для CTE на уровне папки с каскадным слиянием."""
    result_attrs = []
    processed_attrs = set()

    folder_attrs = []
    workflow_attrs = []

    if folder_cte_config:
        folder_cte_q = (
            folder_cte_config.cte_queries.get(cte_name)
            if folder_cte_config.cte_queries
            else None
        )
        if folder_cte_q and folder_cte_q.attributes:
            folder_attrs = list(folder_cte_q.attributes)
        elif folder_cte_config.attributes:
            folder_attrs = list(folder_cte_config.attributes)

    if workflow_cte_config:
        workflow_cte_q = (
            workflow_cte_config.cte_queries.get(cte_name)
            if workflow_cte_config.cte_queries
            else None
        )
        if workflow_cte_q and workflow_cte_q.attributes:
            workflow_attrs = list(workflow_cte_q.attributes)
        elif workflow_cte_config.attributes:
            workflow_attrs = list(workflow_cte_config.attributes)

    for attr in folder_attrs:
        attr_name = attr.name.lower()
        processed_attrs.add(attr_name)
        attr_dict = {
            "name": attr.name,
            "domain_type": ConfigValue(
                value=attr.domain_type, source=folder_source, file=folder_file
            ),
            "required": ConfigValue(
                value=attr.required if hasattr(attr, "required") else False,
                source=folder_source,
                file=folder_file,
            ),
            "default_value": ConfigValue(
                value=attr.default_value if hasattr(attr, "default_value") else None,
                source=folder_source,
                file=folder_file,
            ),
            "constraints": ConfigValue(
                value=list(attr.constraints) if attr.constraints else [],
                source=folder_source,
                file=folder_file,
            ),
            "distribution_key": ConfigValue(
                value=attr.distribution_key
                if hasattr(attr, "distribution_key")
                else None,
                source=folder_source,
                file=folder_file,
            ),
            "partition_key": ConfigValue(
                value=attr.partition_key if hasattr(attr, "partition_key") else None,
                source=folder_source,
                file=folder_file,
            ),
            "description": ConfigValue(
                value=attr.description if hasattr(attr, "description") else "",
                source=folder_source,
                file=folder_file,
            ),
            "is_key": ConfigValue(
                value=attr.is_key if hasattr(attr, "is_key") else False,
                source=folder_source,
                file=folder_file,
            ),
        }
        result_attrs.append(attr_dict)

    for attr in workflow_attrs:
        attr_name = attr.name.lower()
        if attr_name in processed_attrs:
            for attr_dict in result_attrs:
                if attr_dict["name"].lower() == attr_name:
                    if attr.domain_type:
                        attr_dict["domain_type"] = ConfigValue(
                            value=attr.domain_type, source=model_source, file=model_file
                        )
                    if hasattr(attr, "required"):
                        attr_dict["required"] = ConfigValue(
                            value=attr.required, source=model_source, file=model_file
                        )
                    if hasattr(attr, "default_value"):
                        attr_dict["default_value"] = ConfigValue(
                            value=attr.default_value,
                            source=model_source,
                            file=model_file,
                        )
                    if attr.constraints:
                        attr_dict["constraints"] = ConfigValue(
                            value=list(attr.constraints),
                            source=model_source,
                            file=model_file,
                        )
                    if hasattr(attr, "distribution_key"):
                        attr_dict["distribution_key"] = ConfigValue(
                            value=attr.distribution_key,
                            source=model_source,
                            file=model_file,
                        )
                    if hasattr(attr, "partition_key"):
                        attr_dict["partition_key"] = ConfigValue(
                            value=attr.partition_key,
                            source=model_source,
                            file=model_file,
                        )
                    if hasattr(attr, "description"):
                        attr_dict["description"] = ConfigValue(
                            value=attr.description, source=model_source, file=model_file
                        )
                    if hasattr(attr, "is_key"):
                        attr_dict["is_key"] = ConfigValue(
                            value=attr.is_key, source=model_source, file=model_file
                        )
                    break
        else:
            processed_attrs.add(attr_name)
            attr_dict = {
                "name": attr.name,
                "domain_type": ConfigValue(
                    value=attr.domain_type, source=model_source, file=model_file
                ),
                "required": ConfigValue(
                    value=attr.required if hasattr(attr, "required") else False,
                    source=model_source,
                    file=model_file,
                ),
                "default_value": ConfigValue(
                    value=attr.default_value
                    if hasattr(attr, "default_value")
                    else None,
                    source=model_source,
                    file=model_file,
                ),
                "constraints": ConfigValue(
                    value=list(attr.constraints) if attr.constraints else [],
                    source=model_source,
                    file=model_file,
                ),
                "distribution_key": ConfigValue(
                    value=attr.distribution_key
                    if hasattr(attr, "distribution_key")
                    else None,
                    source=model_source,
                    file=model_file,
                ),
                "partition_key": ConfigValue(
                    value=attr.partition_key
                    if hasattr(attr, "partition_key")
                    else None,
                    source=model_source,
                    file=model_file,
                ),
                "description": ConfigValue(
                    value=attr.description if hasattr(attr, "description") else "",
                    source=model_source,
                    file=model_file,
                ),
                "is_key": ConfigValue(
                    value=attr.is_key if hasattr(attr, "is_key") else False,
                    source=model_source,
                    file=model_file,
                ),
            }
            result_attrs.append(attr_dict)

    return result_attrs


def _get_cte_config(
    folder: str,
    folder_config: Optional["FolderConfig"],
    workflow_config: Optional["FolderConfig"],
    context: str,
    folder_path: Path,
) -> Dict[str, Any]:
    """Определить cte конфиг для контекста."""
    folder_yml_path = str(folder_path / "folder.yml")

    folder_cte_config = None
    workflow_cte_config = None
    cte_source: Optional[str] = None
    cte_file: Optional[str] = None

    folder_source = "folder"
    folder_file = folder_yml_path
    model_source = "model"
    model_file = "model.yml"

    if folder_config and folder_config.cte:
        folder_cte_config = folder_config.cte
        cte_source = folder_source
        cte_file = folder_file
    elif workflow_config and workflow_config.cte:
        workflow_cte_config = workflow_config.cte
        cte_source = model_source
        cte_file = model_file

    if folder_cte_config or workflow_cte_config:
        cte_result = {"cte_queries": {}}

        all_cte_names = set()

        if folder_cte_config and folder_cte_config.cte_queries:
            all_cte_names.update(folder_cte_config.cte_queries.keys())
        if workflow_cte_config and workflow_cte_config.cte_queries:
            all_cte_names.update(workflow_cte_config.cte_queries.keys())

        for cte_name in all_cte_names:
            cte_parsed = {}

            cte_parsed["cte_materialization"] = _build_folder_cte_mat_config(
                cte_name=cte_name,
                folder_cte_config=folder_cte_config,
                workflow_cte_config=workflow_cte_config,
                folder_source=folder_source,
                folder_file=folder_file,
                model_source=model_source,
                model_file=model_file,
            )

            cte_parsed["attributes"] = _build_folder_cte_attributes(
                cte_name=cte_name,
                folder_cte_config=folder_cte_config,
                workflow_cte_config=workflow_cte_config,
                folder_source=folder_source,
                folder_file=folder_file,
                model_source=model_source,
                model_file=model_file,
            )

            cte_result["cte_queries"][cte_name] = cte_parsed

        return cte_result

    return {"cte_queries": {}}
