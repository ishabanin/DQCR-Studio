"""ADB validation rules."""

from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.models.sql_object import SQLObjectModel


def _get_config_value(config: Any, key: str, default: Any = None) -> Any:
    """Получить значение из конфига, учитывая ConfigValue."""
    if config is None:
        return default
    if hasattr(config, "value"):
        return config.value
    if isinstance(config, dict):
        return config.get(key, default)
    return default


def _get_file_path(sql_object: "SQLObjectModel", workflow: "WorkflowNewModel") -> str:
    """Compute relative file path from project root."""
    project_name = workflow.project.project_name if workflow.project else ""
    model_group = workflow.models_root
    model_name = workflow.model_name
    sql_path = sql_object.path
    return f"{project_name}/{model_group}/{model_name}/{sql_path}"


def _get_cte_materialization(
    cte_cfg: Any,
    cte_name: str,
    context_name: str,
    tool: str,
    default: str = "ephemeral",
) -> str:
    """Получить материализацию для CTE с учетом ConfigValue."""
    actual_cte_cfg = cte_cfg if not hasattr(cte_cfg, "value") else cte_cfg.value

    if hasattr(actual_cte_cfg, "get_cte_materialization"):
        return actual_cte_cfg.get_cte_materialization(
            cte_name=cte_name,
            context_name=context_name,
            tool=tool,
            default=default,
        )

    if not isinstance(actual_cte_cfg, dict):
        return default

    cte_mat = actual_cte_cfg.get("cte_materialization")
    if not cte_mat:
        return default

    actual_cte_mat = cte_mat if not hasattr(cte_mat, "value") else cte_mat.value

    if not isinstance(actual_cte_mat, dict):
        return str(actual_cte_mat) if actual_cte_mat else default

    by_tool = actual_cte_mat.get("by_tool", {})
    if tool in by_tool:
        tool_cfg = by_tool[tool]
        if hasattr(tool_cfg, "value"):
            return tool_cfg.value
        if isinstance(tool_cfg, dict) and "value" in tool_cfg:
            return tool_cfg["value"]
        return str(tool_cfg) if tool_cfg else default

    default_val = actual_cte_mat.get("default")
    if default_val:
        if hasattr(default_val, "value"):
            return default_val.value
        if isinstance(default_val, dict) and "value" in default_val:
            return default_val["value"]
        return str(default_val)

    return default


class DistributionKeyRule(BaseValidationRule):
    """Проверка наличия ключа распределения для ADB.

    Для материализации insert_fc в ADB требуется ключ распределения.
    """

    name = "adb_distribution_key"
    category = "adb"
    level = ValidationLevel.ERROR
    description = "Проверка наличия ключа распределения для ADB"

    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []

        model_group = workflow.models_root
        model_name = workflow.model_name

        if "adb" not in workflow.tools:
            return issues

        if not workflow.sql_objects:
            return issues

        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue

            for ctx, tool_config in sql_object.config.items():
                available_tools = _get_config_value(tool_config, "tools", [])
                for tool in available_tools:
                    if tool != "adb":
                        continue
                    config = _get_config_value(tool_config, tool)
                    if config is None:
                        continue

                    materialized = _get_config_value(config, "materialized")
                    if materialized is not None:
                        if hasattr(materialized, "value"):
                            mat_value = materialized.value
                        else:
                            mat_value = materialized
                    else:
                        mat_value = None

                    if mat_value != "insert_fc":
                        continue

                    attrs = _get_config_value(config, "attributes", [])
                    has_dist_key = any(
                        _get_config_value(attr, "distribution_key") is not None
                        for attr in attrs
                    )

                    if not has_dist_key:
                        file_path = _get_file_path(sql_object, workflow)
                        issues.append(
                            ValidationIssue(
                                level=self.level,
                                rule=self.name,
                                category=self.category,
                                message="No distribution_key defined for ADB insert_fc materialization",
                                file_path=file_path,
                                model_group=model_group,
                                model_name=model_name,
                                details={"materialization": mat_value, "tool": "adb"},
                            )
                        )

        return issues


class AdbPrimaryKeyRule(BaseValidationRule):
    """Проверка наличия PRIMARY KEY для ADB.

    ADB требует primary key для материализации insert_fc.
    """

    name = "adb_primary_key"
    category = "adb"
    level = ValidationLevel.ERROR
    description = "Проверка наличия PRIMARY KEY для ADB"

    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []

        model_group = workflow.models_root
        model_name = workflow.model_name

        if "adb" not in workflow.tools:
            return issues

        target_table = workflow.target_table
        if not target_table or not target_table.attributes:
            return issues

        has_primary_key = any(attr.is_primary_key() for attr in target_table.attributes)

        if not has_primary_key:
            project_name = workflow.project.project_name if workflow.project else ""
            file_path = f"{project_name}/{model_group}/{model_name}/model.yml"

            issues.append(
                ValidationIssue(
                    level=self.level,
                    rule=self.name,
                    category=self.category,
                    message="No primary key defined in target table for ADB",
                    file_path=file_path,
                    model_group=model_group,
                    model_name=model_name,
                    details={"target_table": target_table.name, "tool": "adb"},
                )
            )

        return issues


class CTEDistributionKeyRule(BaseValidationRule):
    """Проверка наличия ключа распределения для материализованных CTE в ADB.

    Если в запросе есть CTE с материализацией, отличной от ephemeral для tool == adb,
    и у CTE не определен ключ распределения (distribution_key), то это ошибка.
    """

    name = "adb_cte_distribution_key"
    category = "adb"
    level = ValidationLevel.ERROR
    description = "Проверка наличия ключа распределения для материализованных CTE в ADB"

    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []

        model_group = workflow.models_root
        model_name = workflow.model_name

        if "adb" not in workflow.tools:
            return issues

        if not workflow.sql_objects:
            return issues

        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue

            for ctx, tool_config in sql_object.config.items():
                if "cte" not in tool_config:
                    continue

                cte_config = tool_config["cte"]

                if hasattr(cte_config, "cte_queries"):
                    cte_queries = cte_config.cte_queries
                elif isinstance(cte_config, dict):
                    cte_queries = cte_config.get("cte_queries", {})
                else:
                    continue

                if not cte_queries:
                    continue

                for cte_name, cte_cfg in cte_queries.items():
                    materialization = _get_cte_materialization(
                        cte_cfg=cte_cfg,
                        cte_name=cte_name,
                        context_name=ctx,
                        tool="adb",
                        default="ephemeral",
                    )

                    if materialization == "ephemeral":
                        continue

                    actual_cte_cfg = (
                        cte_cfg if not hasattr(cte_cfg, "value") else cte_cfg.value
                    )

                    if hasattr(actual_cte_cfg, "attributes"):
                        attrs = actual_cte_cfg.attributes
                    elif isinstance(actual_cte_cfg, dict):
                        attrs = actual_cte_cfg.get("attributes", [])
                    else:
                        attrs = []

                    has_dist_key = False
                    for attr in attrs:
                        actual_attr = attr if not hasattr(attr, "value") else attr.value
                        if isinstance(actual_attr, dict):
                            dist_key = actual_attr.get("distribution_key")
                            if dist_key is not None:
                                if hasattr(dist_key, "value"):
                                    if dist_key.value is not None:
                                        has_dist_key = True
                                        break
                                elif dist_key is not None:
                                    has_dist_key = True
                                    break
                        elif hasattr(actual_attr, "distribution_key"):
                            dist_key = actual_attr.distribution_key
                            if dist_key is not None:
                                if hasattr(dist_key, "value"):
                                    if dist_key.value is not None:
                                        has_dist_key = True
                                        break
                                else:
                                    has_dist_key = True
                                    break

                    if not has_dist_key:
                        file_path = _get_file_path(sql_object, workflow)
                        issues.append(
                            ValidationIssue(
                                level=self.level,
                                rule=self.name,
                                category=self.category,
                                message=f"CTE '{cte_name}' has materialization '{materialization}' for ADB but no distribution_key defined",
                                file_path=file_path,
                                model_group=model_group,
                                model_name=model_name,
                                details={
                                    "cte_name": cte_name,
                                    "materialization": materialization,
                                    "tool": "adb",
                                },
                            )
                        )

        return issues
