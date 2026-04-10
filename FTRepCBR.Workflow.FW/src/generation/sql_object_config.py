"""SQL Object Config Builder - собирает effective config для SQL-объектов в разрезе контекстов."""

import fnmatch
from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING

from FW.models.sql_object import ConfigValue
from FW.models.attribute import Attribute
from FW.models.enabled import evaluate_condition
from FW.parsing.sql_metadata import SQLMetadataParser

if TYPE_CHECKING:
    from FW.parsing.sql_metadata import SQLMetadata
    from FW.models.configs import QueryConfig, FolderConfig, CTEMaterializationConfig
    from FW.models.project_template import RuleDefinition
    from FW.models.sql_object import SQLObjectModel

def build_sql_object_config(
    folder: str,
    query_name: str,
    query_config: Optional["QueryConfig"],
    folder_config: Optional["FolderConfig"],
    metadata: "SQLMetadata",
    sql_file_path: str,
    contexts: List[str],
    all_contexts: List[str],
    default_materialization: Optional[str],
    folder_path: str,
    get_parent_folder_config: Optional[
        Callable[[str], Optional["FolderConfig"]]
    ] = None,
    template_name: Optional[str] = None,
    folder_rules: Optional[Dict[str, "RuleDefinition"]] = None,
    context_flags: Optional[Dict[str, Dict[str, Any]]] = None,
    context_constants: Optional[Dict[str, Dict[str, Any]]] = None,
    folder_yml_path: Optional[str] = None,
    tools_by_context: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Собрать effective config для всех контекстов SQL-объекта.

    Args:
        folder: имя папки (например, "001_Load__distr")
        query_name: имя запроса (например, "001_RF110_Reg_Acc2")
        query_config: конфиг из model.yml (queries[query_name])
        folder_config: конфиг папки из folder.yml
        metadata: распарсенный SQL с inline конфигами
        sql_file_path: путь к SQL файлу
        contexts: применимые контексты для запроса ["default"]
        all_contexts: все контексты проекта ["default", "vtb"]
        default_materialization: дефолтная материализация из template
        folder_path: полный путь к папке с SQL файлами
        get_parent_folder_config: функция для поиска конфига в родительской папке
        template_name: имя шаблона для заполнения source=template file
        folder_rules: правила для папок из шаблона {pattern: RuleDefinition}

    Returns:
        {
            "default": {
                "materialization": ConfigValue(...),
                "enabled": ConfigValue(...),
                "description": ConfigValue(...),
                "attributes": [...],
                "cte": {...}
            },
            "vtb": {
                "enabled": ConfigValue(value=False, source="folder", file="...", reason="not in enabled.contexts", conditions={...})
            }
        }
    """
    config: Dict[str, Dict[str, Any]] = {}

    inline_query_config = metadata.inline_query_config if metadata else None
    inline_cte_configs = metadata.inline_cte_configs if metadata else {}
    inline_attr_configs = metadata.inline_attr_configs if metadata else {}

    folder_query_cfg = None
    if folder_config and folder_config.queries:
        folder_query_cfg = folder_config.queries.get(query_name)

    applicable_set = set(contexts)
    context_flags = context_flags or {}
    context_constants = context_constants or {}
    tools_by_context = tools_by_context or {}
    all_tools = set()
    for t in tools_by_context.values():
        all_tools.update(t)

    for ctx in all_contexts:
        ctx_key = ctx if ctx else "default"

        reason, info = _get_not_applicable_reason(
            folder=folder,
            query_name=query_name,
            query_config=query_config,
            folder_query_cfg=folder_query_cfg,
            folder_config=folder_config,
            ctx=ctx,
            folder_path=folder_path,
            context_flags=context_flags,
            context_constants=context_constants,
            folder_yml_path=folder_yml_path,
        )

        if reason:
            config[ctx_key] = {
                "enabled": ConfigValue(
                    value=False,
                    source=info.get("source", "default"),
                    file=info.get("file"),
                    reason=reason,
                    conditions=info.get("conditions"),
                ),
            }
            continue

        config[ctx_key] = {}

        config[ctx_key]["tools"] = tools_by_context.get(ctx_key, list(all_tools))

        config[ctx_key]["materialization"] = _get_materialization_config(
            folder=folder,
            query_name=query_name,
            query_config=query_config,
            folder_query_cfg=folder_query_cfg,
            folder_config=folder_config,
            context=ctx,
            default_materialization=default_materialization,
            folder_path=folder_path,
            template_name=template_name,
            folder_rules=folder_rules,
        )

        config[ctx_key]["enabled"] = _get_enabled_config(
            folder=folder,
            query_name=query_name,
            query_config=query_config,
            folder_query_cfg=folder_query_cfg,
            folder_config=folder_config,
            context=ctx,
            folder_path=folder_path,
            folder_yml_path=folder_yml_path,
        )

        config[ctx_key]["description"] = _get_description_config(
            query_name=query_name,
            query_config=query_config,
            inline_config=inline_query_config,
            sql_file_path=sql_file_path,
        )

        config[ctx_key]["attributes"] = _get_attributes_config(
            query_name=query_name,
            query_config=query_config,
            folder_query_cfg=folder_query_cfg,
            folder_config=folder_config,
            inline_attr_configs=inline_attr_configs,
            metadata=metadata,
            sql_file_path=sql_file_path,
            folder_path=folder_path,
        )

        config[ctx_key]["cte"] = _get_cte_config(
            query_name=query_name,
            query_config=query_config,
            folder_query_cfg=folder_query_cfg,
            folder_config=folder_config,
            inline_cte_configs=inline_cte_configs,
            sql_file_path=sql_file_path,
            context=ctx,
            folder_path=folder_path,
            folder=folder,
            metadata=metadata,
        )

    return config


def _get_not_applicable_reason(
    folder: str,
    query_name: str,
    query_config: Optional["QueryConfig"],
    folder_query_cfg: Optional["QueryConfig"],
    folder_config: Optional["FolderConfig"],
    ctx: str,
    folder_path: str,
    context_flags: Optional[Dict[str, Dict[str, Any]]] = None,
    context_constants: Optional[Dict[str, Dict[str, Any]]] = None,
    folder_yml_path: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    """Определить причину неприменимости контекста.

    Returns:
        (reason, info) где info содержит source, file, conditions
    """
    if folder_yml_path is None:
        folder_yml_path = (
            f"{folder_path}/{folder}/folder.yml"
            if folder
            else f"{folder_path}/folder.yml"
        )
    context_flags = context_flags or {}
    context_constants = context_constants or {}
    ctx_flags = context_flags.get(ctx, {})
    ctx_constants = context_constants.get(ctx, {})

    def check_config(
        config_obj: Optional[Any], source: str, file: str
    ) -> tuple[Optional[str], Dict[str, Any]]:
        if config_obj and hasattr(config_obj, "enabled") and config_obj.enabled:
            cfg_contexts = config_obj.enabled.contexts
            conditions = config_obj.enabled.conditions

            if conditions:
                is_satisfied, _ = evaluate_condition(
                    conditions, ctx_flags, ctx_constants
                )
                if not is_satisfied:
                    return "condition not satisfied", {
                        "source": source,
                        "file": file,
                        "conditions": conditions,
                    }
                return None, {"source": source, "file": file, "conditions": conditions}

            if cfg_contexts is None:
                return None, {"source": source, "file": file, "conditions": conditions}

            if ctx in cfg_contexts:
                return None, {"source": source, "file": file, "conditions": conditions}
            else:
                return "not in enabled.contexts", {
                    "source": source,
                    "file": file,
                    "conditions": conditions,
                }

        return None, {"source": "default", "file": None, "conditions": None}

    reason, info = check_config(folder_query_cfg, "folder", folder_yml_path)
    if reason:
        return reason, info

    reason, info = check_config(folder_config, "folder", folder_yml_path)
    if reason:
        return reason, info

    reason, info = check_config(query_config, "model", "model.yml")
    if reason:
        return reason, info

    return None, {"source": "default", "file": None, "conditions": None}


def _get_materialization_config(
    folder: str,
    query_name: str,
    query_config: Optional["QueryConfig"],
    folder_query_cfg: Optional["QueryConfig"],
    folder_config: Optional["FolderConfig"],
    context: str,
    default_materialization: Optional[str],
    folder_path: str,
    template_name: Optional[str] = None,
    folder_rules: Optional[Dict[str, "RuleDefinition"]] = None,
) -> ConfigValue:
    """Определить materialization для контекста."""
    folder_yml_path = (
        f"{folder_path}/{folder}/folder.yml" if folder else f"{folder_path}/folder.yml"
    )

    if folder_query_cfg and folder_query_cfg.materialized:
        return ConfigValue(
            value=folder_query_cfg.materialized, source="folder", file=folder_yml_path
        )

    if query_config and query_config.materialized:
        return ConfigValue(
            value=query_config.materialized, source="model", file="model.yml"
        )

    if folder_config and folder_config.materialized:
        return ConfigValue(
            value=folder_config.materialized, source="folder", file=folder_yml_path
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

    return ConfigValue(value="insert_fc", source="default", file=None)


def _get_enabled_config(
    folder: str,
    query_name: str,
    query_config: Optional["QueryConfig"],
    folder_query_cfg: Optional["QueryConfig"],
    folder_config: Optional["FolderConfig"],
    context: str,
    folder_path: str,
    get_parent_folder_config: Optional[
        Callable[[str], Optional["FolderConfig"]]
    ] = None,
    folder_yml_path: Optional[str] = None,
) -> ConfigValue:
    """Определить enabled для контекста."""
    if folder_yml_path is None:
        folder_yml_path = (
            f"{folder_path}/{folder}/folder.yml"
            if folder
            else f"{folder_path}/folder.yml"
        )

    current_config = folder_query_cfg
    current_path = folder_yml_path
    current_source = "folder"

    if not current_config:
        current_config = folder_config
        if not current_config and get_parent_folder_config:
            parent_folder = folder.rsplit("/", 1)[0] if "/" in folder else ""
            while not current_config and parent_folder:
                current_config = get_parent_folder_config(parent_folder)
                if not current_config:
                    parent_parts = parent_folder.rsplit("/", 1)
                    parent_folder = parent_parts[0] if len(parent_parts) > 1 else ""

    if current_config and current_config.enabled:
        enabled_rule = current_config.enabled
        contexts = enabled_rule.contexts

        if contexts is None or context in contexts:
            result = ConfigValue(value=True, source=current_source, file=current_path)
            result.conditions = enabled_rule.conditions
            return result

    if query_config and query_config.enabled:
        contexts = query_config.enabled.contexts
        if contexts is None or context in contexts:
            result = ConfigValue(value=True, source="model", file="model.yml")
            result.conditions = query_config.enabled.conditions
            return result

    result = ConfigValue(value=True, source="default", file=None)
    result.conditions = None
    return result


def _get_description_config(
    query_name: str,
    query_config: Optional["QueryConfig"],
    inline_config: Optional[Dict[str, Any]],
    sql_file_path: str,
) -> ConfigValue:
    """Определить description для запроса."""
    if inline_config and "description" in inline_config:
        return ConfigValue(
            value=inline_config.get("description"), source="inline", file=sql_file_path
        )

    if query_config and query_config.description:
        return ConfigValue(
            value=query_config.description, source="model", file="model.yml"
        )

    return ConfigValue(value="", source="default", file=None)


def _get_attributes_config(
    query_name: str,
    query_config: Optional["QueryConfig"],
    folder_query_cfg: Optional["QueryConfig"],
    folder_config: Optional["FolderConfig"],
    inline_attr_configs: Dict[str, Dict[str, Any]],
    metadata: "SQLMetadata",
    sql_file_path: str,
    folder_path: str,
) -> List[Dict[str, Any]]:
    """Собрать полный конфиг атрибутов для запроса.

    Каждое свойство атрибута имеет свой source.
    """
    result_attrs = []

    folder_yml_path = f"{folder_path}/folder.yml"

    config_attrs = []
    if folder_query_cfg and folder_query_cfg.attributes:
        config_attrs = list(folder_query_cfg.attributes)
        attr_source = "folder"
        attr_file = folder_yml_path
    elif query_config and query_config.attributes:
        config_attrs = list(query_config.attributes)
        attr_source = "model"
        attr_file = "model.yml"
    else:
        config_attrs = []
        attr_source = None
        attr_file = None

    aliases = metadata.aliases if metadata else []
    attr_names_in_query = {alias.get("alias", "").lower() for alias in aliases}

    processed_attrs = set()

    for attr in config_attrs:
        attr_name = attr.name.lower()
        processed_attrs.add(attr_name)

        attr_dict = {
            "name": attr.name,
            "domain_type": ConfigValue(
                value=attr.domain_type, source=attr_source, file=attr_file
            )
            if attr_source
            else ConfigValue(value="unknown", source="default", file=None),
            "required": ConfigValue(
                value=attr.required if hasattr(attr, "required") else False,
                source=attr_source,
                file=attr_file,
            )
            if attr_source
            else ConfigValue(value=False, source="default", file=None),
            "default_value": ConfigValue(
                value=attr.default_value if hasattr(attr, "default_value") else None,
                source=attr_source,
                file=attr_file,
            )
            if attr_source
            else ConfigValue(value=None, source="default", file=None),
            "constraints": ConfigValue(
                value=list(attr.constraints) if attr.constraints else [],
                source=attr_source,
                file=attr_file,
            )
            if attr_source
            else ConfigValue(value=[], source="default", file=None),
            "distribution_key": ConfigValue(
                value=attr.distribution_key
                if hasattr(attr, "distribution_key")
                else None,
                source=attr_source,
                file=attr_file,
            )
            if attr_source
            else ConfigValue(value=None, source="default", file=None),
            "partition_key": ConfigValue(
                value=attr.partition_key if hasattr(attr, "partition_key") else None,
                source=attr_source,
                file=attr_file,
            )
            if attr_source
            else ConfigValue(value=None, source="default", file=None),
            "description": ConfigValue(
                value=attr.description if hasattr(attr, "description") else "",
                source=attr_source,
                file=attr_file,
            )
            if attr_source
            else ConfigValue(value="", source="default", file=None),
        }

        if attr_name in inline_attr_configs:
            inline_cfg = inline_attr_configs[attr_name]
            for k, v in inline_cfg.items():
                if v is not None:
                    attr_dict[k] = ConfigValue(
                        value=v, source="inline", file=sql_file_path
                    )

        result_attrs.append(attr_dict)

    for alias in aliases:
        attr_name = alias.get("alias", "").lower()
        if attr_name and attr_name not in processed_attrs:
            attr_dict = {
                "name": alias.get("alias", ""),
                "domain_type": ConfigValue(
                    value="unknown", source="default", file=None
                ),
                "required": ConfigValue(value=False, source="default", file=None),
                "default_value": ConfigValue(value=None, source="default", file=None),
                "constraints": ConfigValue(value=[], source="default", file=None),
                "distribution_key": ConfigValue(
                    value=None, source="default", file=None
                ),
                "partition_key": ConfigValue(value=None, source="default", file=None),
                "description": ConfigValue(value="", source="default", file=None),
            }

            if attr_name in inline_attr_configs:
                inline_cfg = inline_attr_configs[attr_name]
                for k, v in inline_cfg.items():
                    if v is not None:
                        attr_dict[k] = ConfigValue(
                            value=v, source="inline", file=sql_file_path
                        )

            result_attrs.append(attr_dict)

    return result_attrs


def _build_cte_mat_config(
    cte_name: str,
    folder_cte_config: Optional["CTEMaterializationConfig"],
    model_cte_config: Optional["CTEMaterializationConfig"],
    inline_cte_cfg: Optional[Dict[str, Any]],
    inline_source: str,
    inline_file: str,
    folder_source: str,
    folder_file: str,
    model_source: str,
    model_file: str,
) -> Dict[str, Any]:
    """Построить вложенную структуру cte_materialization для CTE.

    Каскадное слияние: folder -> model -> inline (inline имеет высший приоритет).
    folder_cte_config - из folder.yml
    model_cte_config - из model.yml
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
    model_cte_q = None

    if folder_cte_config and folder_cte_config.cte_queries:
        folder_cte_q = folder_cte_config.cte_queries.get(cte_name)

    if model_cte_config and model_cte_config.cte_queries:
        model_cte_q = model_cte_config.cte_queries.get(cte_name)

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

    if model_cte_q:
        model_mat = model_cte_q.cte_materialization
        model_by_context = model_cte_q.by_context or {}
        model_by_tool = model_cte_q.by_context or {}

        if model_mat is not None and result["default"].get("value") is None:
            set_entry(result["default"], model_mat, model_source, model_file)
        for ctx, val in model_by_context.items():
            if ctx not in result["by_context"]:
                result["by_context"][ctx] = {
                    "value": val,
                    "source": model_source,
                    "file": model_file,
                }
        for tool, val in model_by_tool.items():
            if tool not in result["by_tool"]:
                result["by_tool"][tool] = {
                    "value": val,
                    "source": model_source,
                    "file": model_file,
                }
    elif model_cte_config:
        model_mat = model_cte_config.cte_materialization
        model_by_context = model_cte_config.by_context or {}
        model_by_tool = model_cte_config.by_tool or {}

        if model_mat is not None and result["default"].get("value") is None:
            set_entry(result["default"], model_mat, model_source, model_file)
        for ctx, val in model_by_context.items():
            if ctx not in result["by_context"]:
                result["by_context"][ctx] = {
                    "value": val,
                    "source": model_source,
                    "file": model_file,
                }
        for tool, val in model_by_tool.items():
            if tool not in result["by_tool"]:
                result["by_tool"][tool] = {
                    "value": val,
                    "source": model_source,
                    "file": model_file,
                }

    if inline_cte_cfg and "cte_materialization" in inline_cte_cfg:
        inline_mat = inline_cte_cfg["cte_materialization"]
        if isinstance(inline_mat, str):
            set_entry(result["default"], inline_mat, inline_source, inline_file)
        elif isinstance(inline_mat, dict):
            if "default" in inline_mat and inline_mat["default"] is not None:
                set_entry(
                    result["default"], inline_mat["default"], inline_source, inline_file
                )
            if "by_context" in inline_mat:
                for ctx, val in inline_mat["by_context"].items():
                    if val is not None:
                        result["by_context"][ctx] = {
                            "value": val,
                            "source": inline_source,
                            "file": inline_file,
                        }
            if "by_tool" in inline_mat:
                for tool, val in inline_mat["by_tool"].items():
                    if val is not None:
                        result["by_tool"][tool] = {
                            "value": val,
                            "source": inline_source,
                            "file": inline_file,
                        }

    return result


def _build_cte_attributes(
    cte_name: str,
    folder_cte_config: Optional["CTEMaterializationConfig"],
    model_cte_config: Optional["CTEMaterializationConfig"],
    inline_cte_cfg: Optional[Dict[str, Any]],
    inline_source: str,
    inline_file: str,
    folder_source: str,
    folder_file: str,
    model_source: str,
    model_file: str,
    sql_parser: Optional[SQLMetadataParser] = None,
    source_sql: Optional[str] = None,
    sql_source: str = "sql",
    sql_file: str = "",
) -> List[Dict[str, Any]]:
    """Построить список атрибутов для CTE с каскадным слиянием.

    folder_cte_config - из folder.yml
    model_cte_config - из model.yml
    """
    result_attrs = []
    processed_attrs = set()

    folder_attrs = []
    model_attrs = []
    inline_attrs = []

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

    if model_cte_config:
        model_cte_q = (
            model_cte_config.cte_queries.get(cte_name)
            if model_cte_config.cte_queries
            else None
        )
        if model_cte_q and model_cte_q.attributes:
            model_attrs = list(model_cte_q.attributes)
        elif model_cte_config.attributes and not folder_attrs:
            model_attrs = list(model_cte_config.attributes)

    if inline_cte_cfg and "attributes" in inline_cte_cfg:
        inline_attrs = inline_cte_cfg["attributes"]

    sql_aliases = []
    if sql_parser and source_sql:
        try:
            cte_metadata = sql_parser.parse(source_sql)
            if cte_metadata and cte_metadata.aliases:
                for alias in cte_metadata.aliases:
                    sql_aliases.append(alias.get("alias", ""))
        except Exception:
            pass

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

        for inline_attr in inline_attrs:
            if inline_attr.get("name", "").lower() == attr_name:
                for k, v in inline_attr.items():
                    if k != "name" and v is not None:
                        attr_dict[k] = ConfigValue(
                            value=v, source=inline_source, file=inline_file
                        )
                break

        result_attrs.append(attr_dict)

    for attr in model_attrs:
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

            for inline_attr in inline_attrs:
                if inline_attr.get("name", "").lower() == attr_name:
                    for k, v in inline_attr.items():
                        if k != "name" and v is not None:
                            attr_dict[k] = ConfigValue(
                                value=v, source=inline_source, file=inline_file
                            )
                    break

            result_attrs.append(attr_dict)

    inline_attr_names = {a.get("name", "").lower() for a in inline_attrs}
    for attr_name in inline_attr_names:
        if attr_name not in processed_attrs:
            for inline_attr in inline_attrs:
                if inline_attr.get("name", "").lower() == attr_name:
                    attr_dict = {
                        "name": inline_attr.get("name", ""),
                        "domain_type": ConfigValue(
                            value=inline_attr.get("domain_type", "unknown"),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "required": ConfigValue(
                            value=inline_attr.get("required", False),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "default_value": ConfigValue(
                            value=inline_attr.get("default_value"),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "constraints": ConfigValue(
                            value=inline_attr.get("constraints", []),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "distribution_key": ConfigValue(
                            value=inline_attr.get("distribution_key"),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "partition_key": ConfigValue(
                            value=inline_attr.get("partition_key"),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "description": ConfigValue(
                            value=inline_attr.get("description", ""),
                            source=inline_source,
                            file=inline_file,
                        ),
                        "is_key": ConfigValue(
                            value=inline_attr.get("is_key", False),
                            source=inline_source,
                            file=inline_file,
                        ),
                    }
                    result_attrs.append(attr_dict)
                    break

    if not result_attrs and sql_aliases:
        for alias_name in sql_aliases:
            attr_dict = {
                "name": alias_name,
                "domain_type": ConfigValue(
                    value="unknown", source=sql_source, file=sql_file
                ),
                "required": ConfigValue(value=False, source=sql_source, file=sql_file),
                "default_value": ConfigValue(
                    value=None, source=sql_source, file=sql_file
                ),
                "constraints": ConfigValue(value=[], source=sql_source, file=sql_file),
                "distribution_key": ConfigValue(
                    value=None, source=sql_source, file=sql_file
                ),
                "partition_key": ConfigValue(
                    value=None, source=sql_source, file=sql_file
                ),
                "description": ConfigValue(value="", source=sql_source, file=sql_file),
            }

            if inline_cte_cfg:
                for k, v in inline_cte_cfg.items():
                    if v is not None and k in attr_dict:
                        attr_dict[k] = ConfigValue(
                            value=v, source=inline_source, file=inline_file
                        )

            result_attrs.append(attr_dict)

    if result_attrs and inline_cte_cfg:
        for attr_dict in result_attrs:
            attr_name = attr_dict["name"].lower()
            for k, v in inline_cte_cfg.items():
                if v is not None and k in attr_dict:
                    attr_dict[k] = ConfigValue(
                        value=v, source=inline_source, file=inline_file
                    )

    return result_attrs


def _get_cte_config(
    query_name: str,
    query_config: Optional["QueryConfig"],
    folder_query_cfg: Optional["QueryConfig"],
    folder_config: Optional["FolderConfig"],
    inline_cte_configs: Dict[str, Dict[str, Any]],
    sql_file_path: str,
    context: str,
    folder_path: str,
    folder: str = "",
    metadata: Optional["SQLMetadata"] = None,
) -> Dict[str, Any]:
    """Собрать CTE конфиг для запроса с учетом контекста."""
    cte_result = {}

    folder_cte_config = None
    model_cte_config = None

    folder_source = "folder"
    folder_file = (
        f"{folder_path}/{folder}/folder.yml" if folder else f"{folder_path}/folder.yml"
    )
    model_source = "model"
    model_file = "model.yml"
    inline_source = "inline"
    inline_file = sql_file_path

    sql_source = "sql"
    sql_file = sql_file_path

    if folder_query_cfg and folder_query_cfg.cte:
        folder_cte_config = folder_query_cfg.cte
    elif folder_config and folder_config.cte:
        folder_cte_config = folder_config.cte

    if query_config and query_config.cte:
        model_cte_config = query_config.cte

    all_cte_names = set()
    if inline_cte_configs:
        all_cte_names.update(inline_cte_configs.keys())
    if folder_cte_config and folder_cte_config.cte_queries:
        all_cte_names.update(folder_cte_config.cte_queries.keys())
    if model_cte_config and model_cte_config.cte_queries:
        all_cte_names.update(model_cte_config.cte_queries.keys())

    if all_cte_names:
        cte_result["cte_queries"] = {}

        for cte_name in all_cte_names:
            cte_parsed = {}

            inline_cfg = (
                inline_cte_configs.get(cte_name) if inline_cte_configs else None
            )

            cte_parsed["cte_materialization"] = _build_cte_mat_config(
                cte_name=cte_name,
                folder_cte_config=folder_cte_config,
                model_cte_config=model_cte_config,
                inline_cte_cfg=inline_cfg,
                inline_source=inline_source,
                inline_file=inline_file,
                folder_source=folder_source,
                folder_file=folder_file,
                model_source=model_source,
                model_file=model_file,
            )

            cte_parsed["attributes"] = _build_cte_attributes(
                cte_name=cte_name,
                folder_cte_config=folder_cte_config,
                model_cte_config=model_cte_config,
                inline_cte_cfg=inline_cfg,
                inline_source=inline_source,
                inline_file=inline_file,
                folder_source=folder_source,
                folder_file=folder_file,
                model_source=model_source,
                model_file=model_file,
                sql_parser=SQLMetadataParser()
                if metadata and hasattr(metadata, "cte") and cte_name in metadata.cte
                else None,
                source_sql=metadata.cte[cte_name].get("cte_source_sql")
                if metadata and hasattr(metadata, "cte") and cte_name in metadata.cte
                else None,
                sql_source=sql_source,
                sql_file=sql_file,
            )

            cte_result["cte_queries"][cte_name] = cte_parsed
    else:
        cte_result["cte_queries"] = {}

    return cte_result


def build_compiled_sql_object(
    sql_object: "SQLObjectModel",
    metadata: "SQLMetadata",
    all_contexts: List[str],
    tools_by_context: Dict[str, List[str]],
    all_tools: List[str],
) -> None:
    """Заполнить compiled для SQL объекта.

    Заполняется только для enabled контекстов и их tools.
    """
    compiled: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for ctx in all_contexts:
        ctx_config = sql_object.config.get(ctx, {})
        enabled_value = ctx_config.get("enabled")

        is_enabled = True
        if enabled_value is not None:
            if isinstance(enabled_value, ConfigValue):
                is_enabled = enabled_value.value is True
            else:
                is_enabled = enabled_value is True

        if not is_enabled:
            continue

        tools = tools_by_context.get(ctx, all_tools)

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
                "prepared_sql": sql_object.source_sql,
                "rendered_sql": "",
            }

    sql_object.compiled = compiled
