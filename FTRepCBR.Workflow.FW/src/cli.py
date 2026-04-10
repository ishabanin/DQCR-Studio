"""CLI interface for FW."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from FW.models import (
    SQLMetadataParser,
    ParameterModel,
    SQLQueryModel,
)
from FW.generation import get_builder
from FW.config import (
    get_tool_registry,
    get_workflow_engine_registry,
    get_template_registry,
)
from FW.macros import get_macro_registry, get_function_registry
from FW.parsing import load_template, load_project_config, list_templates
from FW.logging_config import setup_logging
from FW.exceptions import TemplateNotFoundError, ConfigValidationError
from FW.validation import (
    RuleRunner,
    validate_template,
    generate_html_report,
    generate_json_report,
    ValidationReport,
)


def parse_sql_command(sql_path: str, output: str = None):
    """Парсить SQL файл - получить metadata."""
    parser = SQLMetadataParser()

    sql_file = Path(sql_path)
    if not sql_file.exists():
        print(f"Error: File not found: {sql_path}", file=sys.stderr)
        sys.exit(1)

    with open(sql_file, "r", encoding="utf-8") as f:
        content = f.read()

    metadata = parser.parse(content)
    result = metadata.to_dict()

    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output, encoding="utf-8")
        print(f"Result saved to: {output}")
    else:
        print(json_output)


def parse_sql_model_command(sql_path: str, output: str = None):
    """Парсить SQL файл - получить полную SQLQueryModel."""
    parser = SQLMetadataParser()

    sql_file = Path(sql_path)
    if not sql_file.exists():
        print(f"Error: File not found: {sql_path}", file=sys.stderr)
        sys.exit(1)

    with open(sql_file, "r", encoding="utf-8") as f:
        content = f.read()

    metadata = parser.parse(content)

    sql_model = SQLQueryModel(
        name=sql_file.stem,
        path=sql_file,
        source_sql=content,
        metadata=metadata,
        materialization="insert_fc",
        context="all",
    )

    result = sql_model.to_dict()
    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output, encoding="utf-8")
        print(f"Result saved to: {output}")
    else:
        print(json_output)


def parse_parameter_command(param_path: str, output: str = None):
    """Парсить файл параметра."""
    import yaml

    param_file = Path(param_path)
    if not param_file.exists():
        print(f"Error: File not found: {param_file}", file=sys.stderr)
        sys.exit(1)

    with open(param_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "parameter" not in data:
        print(f"Error: Invalid parameter file format", file=sys.stderr)
        sys.exit(1)

    param_model = ParameterModel.from_dict(param_file.stem, data)

    result = param_model.to_dict()
    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output, encoding="utf-8")
        print(f"Result saved to: {output}")
    else:
        print(json_output)


def build_command(
    project_path: str,
    model_groups: list = None,
    model_name: str = None,
    context: str = None,
    output: str = None,
):
    """Построить WorkflowModel (абстрактную, без workflow engine)."""
    setup_logging(level="INFO")

    project = Path(project_path)
    if not project.exists():
        print(f"Error: Project not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    tool_registry = get_tool_registry()
    macro_registry = get_macro_registry()
    function_registry = get_function_registry(tool_registry.tools)

    project_config = load_project_config(project)

    if not project_config or not project_config.template:
        available = list_templates()
        raise TemplateNotFoundError(
            f"Template not specified in project.yml. Available templates: {available}"
        )

    template_registry = get_template_registry()
    template = template_registry.get(project_config.template)

    if not template:
        available = list_templates()
        raise TemplateNotFoundError(
            f"Template '{project_config.template}' not found. "
            f"Available templates: {available}"
        )

    if not template.models:
        raise TemplateNotFoundError(
            f"Template '{project_config.template}' has no models defined"
        )

    results = []
    for model_definition in template.models:
        if model_groups and not (model_definition.name in model_groups):
            continue
        # Определить какой builder использовать
        builder_name = "default"
        if model_definition.config and model_definition.config.builder:
            builder_name = model_definition.config.builder
        elif template.config and template.config.builder:
            builder_name = template.config.builder

        builder = get_builder(
            builder_name,
            project_path=project,
            tool_registry=tool_registry,
            macro_registry=macro_registry,
            function_registry=function_registry,
            context_name=context,
            template=template,
            model_definition=model_definition,
        )

        if model_name:
            workflow_model = builder.build(model_name, context)
            result = workflow_model.to_dict()
            json_output = json.dumps(result, indent=2, ensure_ascii=False)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json_output, encoding="utf-8")
                print(f"Workflow model saved to: {output}")
            else:
                print(json_output)

            results.append(result)
        else:
            workflows = builder.build_all(context)
            result = {name: wf.to_dict() for name, wf in workflows.items()}
            json_output = json.dumps(result, indent=2, ensure_ascii=False)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json_output, encoding="utf-8")
                print(f"Workflow models saved to: {output}")
            else:
                print(json_output)

            results.append(result)
    return results


def generate_command(
    project_path: str,
    model_groups: list = None,
    model_name: str = None,
    context: str = None,
    output: str = None,
    workflow_engine: str = None,
):
    """Сгенерировать workflow файлы с учётом workflow engine.

    Args:
        context: Если None - строится полная модель без фильтрации по контексту.
                Если указан (например, "default") - модель для конкретного контекста.
    """
    setup_logging(level="INFO")

    project = Path(project_path)
    if not project.exists():
        print(f"Error: Project not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    tool_registry = get_tool_registry()
    macro_registry = get_macro_registry()
    function_registry = get_function_registry(tool_registry.tools)
    workflow_engine_registry = get_workflow_engine_registry()

    project_config = load_project_config(project)

    if not project_config or not project_config.template:
        available = list_templates()
        raise TemplateNotFoundError(
            f"Template not specified in project.yml. Available templates: {available}"
        )

    template_registry = get_template_registry()
    template = template_registry.get(project_config.template)

    if not template:
        available = list_templates()
        raise TemplateNotFoundError(
            f"Template '{project_config.template}' not found. "
            f"Available templates: {available}"
        )

    if not template.models:
        raise TemplateNotFoundError(
            f"Template '{project_config.template}' has no models defined"
        )

    for model_definition in template.models:
        if model_groups and not (model_definition.name in model_groups):
            continue

        # If model_name is specified, check if this model contains it
        if model_name:
            model_dir = project / model_definition.paths.models_root
            if not (model_dir / model_name).exists():
                continue

        builder_name = (
            model_definition.config.builder if model_definition.config else "default"
        )

        if not workflow_engine:
            if model_definition.config and model_definition.config.workflow_engine:
                workflow_engine = model_definition.config.workflow_engine

        if not workflow_engine:
            raise ConfigValidationError(
                "workflow_engine must be specified either in template config or via -w CLI option",
                field="workflow_engine",
            )

        from FW.generation.builder_registry import get_builder

        builder = get_builder(
            name=builder_name,
            project_path=project,
            tool_registry=tool_registry,
            macro_registry=macro_registry,
            function_registry=function_registry,
            context_name=context,
            template=template,
            model_definition=model_definition,
        )

        if workflow_engine:
            builder_with_engine = get_builder(
                name=builder_name,
                project_path=project,
                tool_registry=tool_registry,
                macro_registry=macro_registry,
                function_registry=function_registry,
                context_name=context,
                workflow_engine=workflow_engine,
                template=template,
                model_definition=model_definition,
            )
        else:
            builder_with_engine = None

        if model_name:
            if builder_with_engine:
                workflow_model = builder_with_engine.build(model_name, context)
            else:
                workflow_model = builder.build(model_name, context)

            output_dir = (
                Path(output) if output else project / model_definition.paths.target
            )
            target_path = output_dir
            target_path.mkdir(parents=True, exist_ok=True)

            from FW.macros.env import WorkflowMacroEnv

            env = WorkflowMacroEnv(
                workflow=workflow_model,
                macro_registry=macro_registry,
                target_path=target_path,
                tools=tool_registry.tools,
            )

            workflow_template = None
            if workflow_model.template and workflow_model.template.value:
                workflow_template = workflow_model.template.value
            elif model_definition.config and model_definition.config.workflow_template:
                workflow_template = model_definition.config.workflow_template

            if workflow_template and macro_registry.has_workflow_template(
                workflow_engine, workflow_template
            ):
                workflow_macro = macro_registry.get_workflow_template(
                    workflow_engine, workflow_template
                )
            else:
                workflow_macro = macro_registry.get_python_macro(
                    "workflow", workflow_engine
                )

            workflow_macro(workflow=workflow_model, env=env)

            print(f"Generated workflow in: {target_path}")
        else:
            if not macro_registry.has_python_macro("workflow", workflow_engine):
                print(
                    f"Error: Python workflow macro not found for '{workflow_engine}'",
                    file=sys.stderr,
                )
                return

            if builder_with_engine:
                workflows = builder_with_engine.build_all(context)
            else:
                workflows = builder.build_all(context)

            output_dir = (
                Path(output) if output else project / model_definition.paths.target
            )

            for name, workflow_model in workflows.items():
                target_path = output_dir
                target_path.mkdir(parents=True, exist_ok=True)

                from FW.macros.env import WorkflowMacroEnv

                env = WorkflowMacroEnv(
                    workflow=workflow_model,
                    macro_registry=macro_registry,
                    target_path=target_path,
                    tools=tool_registry.tools,
                )

                workflow_template = None
                if workflow_model.template and workflow_model.template.value:
                    workflow_template = workflow_model.template.value
                elif (
                    model_definition.config
                    and model_definition.config.workflow_template
                ):
                    workflow_template = model_definition.config.workflow_template

                if workflow_template and macro_registry.has_workflow_template(
                    workflow_engine, workflow_template
                ):
                    workflow_macro = macro_registry.get_workflow_template(
                        workflow_engine, workflow_template
                    )
                else:
                    workflow_macro = macro_registry.get_python_macro(
                        "workflow", workflow_engine
                    )

                workflow_macro(workflow=workflow_model, env=env)

                print(f"Generated workflow: {target_path}")


def validate_command(
    project_path: str,
    model_name: str = None,
    context: str = None,
    output: str = None,
    categories: str = None,
):
    """Валидация проекта.

    Проверяет проект по шаблону и запускает набор правил валидации.

    Args:
        project_path: Путь к проекту
        model_name: Имя модели (опционально)
        context: Имя контекста (опционально)
        output: Директория для сохранения отчётов (опционально)
        categories: Список категорий правил через запятую (опционально)
    """
    from datetime import datetime

    setup_logging(level="INFO")

    project = Path(project_path)
    if not project.exists():
        print(f"Error: Project not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    tool_registry = get_tool_registry()
    macro_registry = get_macro_registry()
    function_registry = get_function_registry(tool_registry.tools)

    project_config = load_project_config(project)

    if not project_config or not project_config.template:
        available = list_templates()
        raise TemplateNotFoundError(
            f"Template not specified in project.yml. Available templates: {available}"
        )

    template_registry = get_template_registry()
    template = template_registry.get(project_config.template)

    if not template:
        available = list_templates()
        raise TemplateNotFoundError(
            f"Template '{project_config.template}' not found. "
            f"Available templates: {available}"
        )

    if not template.models:
        raise TemplateNotFoundError(
            f"Template '{project_config.template}' has no models defined"
        )

    output_dir = Path(output) if output else project / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    available_model_groups = [md.name for md in template.models]
    available_workflows: Dict[str, List[str]] = {}
    all_issues = []
    all_template_issues = []

    def process_model_definition(model_def, model_group_name: str):
        """Обработать одну model_definition."""
        validation_categories = []
        if categories:
            validation_categories = [c.strip() for c in categories.split(",")]
        else:
            validation_categories = (
                model_def.validation_categories
                if model_def.validation_categories
                else ["general"]
            )

        builder_name = "default"
        if model_def.config and model_def.config.builder:
            builder_name = model_def.config.builder
        elif template.config and template.config.builder:
            builder_name = template.config.builder

        from FW.generation.builder_registry import get_builder
        builder = get_builder(
            builder_name,
            project_path=project,
            tool_registry=tool_registry,
            macro_registry=macro_registry,
            function_registry=function_registry,
            context_name=context,
            template=template,
            model_definition=model_def,
        )

        workflows = builder.build_all(context)
        
        if model_group_name not in available_workflows:
            available_workflows[model_group_name] = []
        
        model_issues = []
        model_template_issues = []
        
        for wf_name, workflow_model in workflows.items():
            available_workflows[model_group_name].append(wf_name)
            
            template_issues = validate_template(workflow_model, template)
            for ti in template_issues:
                ti.model_group = model_group_name
                ti.model_name = wf_name
            model_template_issues.extend(template_issues)

            runner = RuleRunner(validation_categories)
            rule_issues = runner.run(workflow_model)
            for ri in rule_issues:
                ri.model_group = model_group_name
                ri.model_name = wf_name
            model_issues.extend(rule_issues)
        
        return model_issues, model_template_issues, workflows.keys()

    for model_def in template.models:
        model_group_name = model_def.name
        
        model_issues, model_template_issues, wf_names = process_model_definition(model_def, model_group_name)
        all_issues.extend(model_issues)
        all_template_issues.extend(model_template_issues)

    validation_categories = categories.split(",") if categories else ["general"]

    if model_name:
        filtered_issues = [i for i in all_issues if i.model_name == model_name]
        filtered_template_issues = [i for i in all_template_issues if i.model_name == model_name]
        
        report = ValidationReport(
            project_name=project_config.name,
            model_name=model_name,
            template_name=project_config.template,
            validation_categories=validation_categories,
            timestamp=datetime.now().isoformat(),
            model_group="",
            available_model_groups=available_model_groups,
            available_workflows=available_workflows,
            issues=filtered_issues,
            template_issues=filtered_template_issues,
        )

        json_path = output_dir / f"{model_name}_validation.json"
        html_path = output_dir / f"{model_name}_validation.html"

        generate_json_report(report, str(json_path))
        generate_html_report(report, str(html_path))

        print(f"Validation report for '{model_name}':")
        print(f"  Total issues: {report.total_issues}")
        print(f"  Errors: {report.error_count}")
        print(f"  Warnings: {report.warning_count}")
        print(f"  Info: {report.info_count}")
        print(f"\nJSON: {json_path}")
        print(f"HTML: {html_path}")

        return report
    else:
        report = ValidationReport(
            project_name=project_config.name,
            model_name="",
            template_name=project_config.template,
            validation_categories=validation_categories,
            timestamp=datetime.now().isoformat(),
            model_group="",
            available_model_groups=available_model_groups,
            available_workflows=available_workflows,
            issues=all_issues,
            template_issues=all_template_issues,
        )

        json_path = output_dir / "validation_summary.json"
        html_path = output_dir / "validation_summary.html"

        generate_json_report(report, str(json_path))
        generate_html_report(report, str(html_path))

        total_errors = report.error_count
        total_warnings = report.warning_count
        total_info = report.info_count

        print(f"Validation complete for {len(available_model_groups)} model groups:")
        print(f"  Model groups: {', '.join(available_model_groups)}")
        print(f"  Total errors: {total_errors}")
        print(f"  Total warnings: {total_warnings}")
        print(f"  Total info: {total_info}")
        print(f"\nJSON: {json_path}")
        print(f"HTML: {html_path}")

        return report


def main():
    """Точка входа."""
    parser = argparse.ArgumentParser(prog="fw2", description="DQCR Framework v2")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    parse_sql_parser = subparsers.add_parser(
        "parse-sql", help="Parse SQL file (metadata only)"
    )
    parse_sql_parser.add_argument("sql_path", help="Path to SQL file")
    parse_sql_parser.add_argument("-o", "--output", help="Output file path")

    parse_sql_model_parser = subparsers.add_parser(
        "parse-sql-model", help="Parse SQL file to full SQLQueryModel"
    )
    parse_sql_model_parser.add_argument("sql_path", help="Path to SQL file")
    parse_sql_model_parser.add_argument("-o", "--output", help="Output file path")

    parse_param_parser = subparsers.add_parser(
        "parse-parameter", help="Parse parameter file"
    )
    parse_param_parser.add_argument("param_path", help="Path to parameter YAML file")
    parse_param_parser.add_argument("-o", "--output", help="Output file path")

    build_parser = subparsers.add_parser("build", help="Build workflow model")
    build_parser.add_argument("project_path", help="Path to project")
    build_parser.add_argument("model_name", nargs="?", help="Model name (optional)")
    build_parser.add_argument("-c", "--context", default=None, help="Context name")
    build_parser.add_argument("-o", "--output", help="Output file path")
    build_parser.add_argument(
        "-w",
        "--workflow-engine",
        default=None,
        help="Workflow engine (airflow, dbt, oracle_plsql)",
    )

    generate_parser = subparsers.add_parser("generate", help="Generate workflow files")
    generate_parser.add_argument("project_path", help="Path to project")
    generate_parser.add_argument("model_name", nargs="?", help="Model name (optional)")
    generate_parser.add_argument(
        "-c", "--context", default="default", help="Context name"
    )
    generate_parser.add_argument("-o", "--output", help="Output directory")
    generate_parser.add_argument(
        "-w",
        "--workflow-engine",
        default=None,
        help="Workflow engine (airflow, dbt, oracle_plsql)",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate project")
    validate_parser.add_argument("project_path", help="Path to project")
    validate_parser.add_argument("model_name", nargs="?", help="Model name (optional)")
    validate_parser.add_argument("-c", "--context", default=None, help="Context name")
    validate_parser.add_argument("-o", "--output", help="Output directory for reports")
    validate_parser.add_argument(
        "-r",
        "--rules",
        default=None,
        help="Validation categories (comma-separated): general, sql, adb, descriptions",
    )

    args = parser.parse_args()

    try:
        if args.command == "parse-sql":
            parse_sql_command(args.sql_path, args.output)
        elif args.command == "parse-sql-model":
            parse_sql_model_command(args.sql_path, args.output)
        elif args.command == "parse-parameter":
            parse_parameter_command(args.param_path, args.output)
        elif args.command == "build":
            build_command(args.project_path, args.model_name, args.context, args.output)
        elif args.command == "generate":
            generate_command(
                args.project_path,
                model_name=args.model_name,
                context=args.context,
                output=args.output,
                workflow_engine=args.workflow_engine,
            )
        elif args.command == "validate":
            validate_command(
                args.project_path,
                args.model_name,
                args.context,
                args.output,
                args.rules,
            )
        else:
            parser.print_help()
    except TemplateNotFoundError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
