from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import HTTPException

from app.core.fs import resolve_project_path


class FWError(Exception):
    def __init__(self, detail: str, status_code: int = 500, code: str = "fw_error") -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code


class FWNotFoundError(FWError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=404, code="fw_not_found")


class FWValidationError(FWError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=400, code="fw_validation_error")


class FWExecutionError(FWError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, status_code=500, code="fw_execution_error")


@dataclass(frozen=True)
class TemplateRegistry:
    templates: tuple[str, ...]


LineageNodesBuilder = Callable[[Path, str], tuple[list[dict[str, object]], int]]
LineageEdgesBuilder = Callable[[list[dict[str, object]]], list[dict[str, str]]]
ValidationRunner = Callable[[Path, str, str, list[str] | None], dict[str, object]]
GenerationRunner = Callable[[Path, str, str, str, str, bool, str | None], dict[str, object]]
ModelLoader = Callable[[Path, str], Path]


class FWService:
    def __init__(
        self,
        *,
        projects_base_path: Path,
        model_loader: ModelLoader,
        lineage_nodes_builder: LineageNodesBuilder,
        lineage_edges_builder: LineageEdgesBuilder,
        validation_runner: ValidationRunner,
        generation_runner: GenerationRunner,
        template_registry: TemplateRegistry | None = None,
        cli_command: str = "fw2",
        prefer_cli: bool = True,
    ) -> None:
        self._projects_base_path = projects_base_path
        self._model_loader = model_loader
        self._lineage_nodes_builder = lineage_nodes_builder
        self._lineage_edges_builder = lineage_edges_builder
        self._validation_runner = validation_runner
        self._generation_runner = generation_runner
        self._cli_command = cli_command
        self._prefer_cli = prefer_cli
        self._template_registry = template_registry or TemplateRegistry(
            templates=("dqcr", "airflow", "dbt", "oracle_plsql")
        )

    @property
    def template_registry(self) -> TemplateRegistry:
        return self._template_registry

    def _cli_available(self) -> bool:
        return bool(self._cli_command) and shutil.which(self._cli_command) is not None

    def _run_cli_command(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self._cli_command, *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise FWExecutionError(f"Failed to execute framework CLI '{self._cli_command}': {exc}") from exc

    @staticmethod
    def _extract_location_parts(location: str | None) -> tuple[str | None, int | None]:
        if not location:
            return None, None
        if ":" not in location:
            return location, None
        file_path, maybe_line = location.rsplit(":", 1)
        try:
            return file_path, int(maybe_line)
        except ValueError:
            return location, None

    def _run_validation_via_cli(
        self,
        project_path: Path,
        project_id: str,
        model_id: str,
        rules: list[str] | None,
    ) -> dict[str, object]:
        run_id = f"val-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        output_dir = project_path / ".dqcr_validation_runs" / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        args = ["validate", str(project_path), model_id, "-o", str(output_dir)]
        if rules:
            args.extend(["-r", ",".join(rules)])

        completed = self._run_cli_command(args)
        json_report = output_dir / f"{model_id}_validation.json"

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            details = stderr or stdout or f"Framework CLI exited with code {completed.returncode}."
            raise FWExecutionError(f"Framework validation failed: {details}")

        if not json_report.exists():
            raise FWExecutionError(f"Framework validation finished without JSON report: {json_report}")

        data = json.loads(json_report.read_text(encoding="utf-8"))
        issues = []
        for item in data.get("template_issues", []):
            if isinstance(item, dict):
                item = {**item, "category": item.get("category") or "template"}
                issues.append(item)
        for item in data.get("issues", []):
            if isinstance(item, dict):
                issues.append(item)

        normalized_rules: list[dict[str, object]] = []
        for item in issues:
            level = str(item.get("level", "warning")).lower()
            file_path, line = self._extract_location_parts(item.get("location"))
            normalized_rules.append(
                {
                    "rule_id": str(item.get("rule", "framework.unknown")),
                    "name": str(item.get("rule", "framework.unknown")),
                    "status": "error" if level == "error" else "warning" if level == "warning" else "pass",
                    "message": str(item.get("message", "")),
                    "file_path": file_path,
                    "line": line,
                }
            )

        summary = data.get("summary", {})
        return {
            "run_id": run_id,
            "timestamp": data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "project": project_id,
            "model": model_id,
            "summary": {
                "passed": int(summary.get("info", 0)),
                "warnings": int(summary.get("warnings", 0)),
                "errors": int(summary.get("errors", 0)),
            },
            "rules": normalized_rules,
            "engine": "framework_cli",
            "artifacts": {
                "json_report": str(json_report.relative_to(project_path)),
                "html_report": str((output_dir / f"{model_id}_validation.html").relative_to(project_path)),
            },
        }

    def _run_generation_via_cli(
        self,
        project_path: Path,
        project_id: str,
        model_id: str,
        engine: str,
        context: str,
        output_path: str | None,
    ) -> dict[str, object]:
        build_id = f"bld-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        relative_output = Path(output_path.strip()) / build_id if output_path and output_path.strip() else Path(".dqcr_builds") / build_id
        absolute_output = project_path / relative_output
        absolute_output.mkdir(parents=True, exist_ok=True)

        args = [
            "generate",
            str(project_path),
            model_id,
            "-c",
            context,
            "-w",
            engine,
            "-o",
            str(absolute_output),
        ]
        completed = self._run_cli_command(args)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            details = stderr or stdout or f"Framework CLI exited with code {completed.returncode}."
            raise FWExecutionError(f"Framework generation failed: {details}")

        files: list[dict[str, object]] = []
        for file_path in sorted(absolute_output.rglob("*"), key=lambda item: str(item).lower()):
            if not file_path.is_file():
                continue
            files.append(
                {
                    "path": str(file_path.relative_to(absolute_output)),
                    "source_path": None,
                    "size_bytes": file_path.stat().st_size,
                }
            )

        return {
            "build_id": build_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project_id,
            "model": model_id,
            "engine": engine,
            "context": context,
            "dry_run": False,
            "output_path": str(relative_output),
            "files_count": len(files),
            "files": files,
            "execution_mode": "framework_cli",
        }

    @staticmethod
    def _normalize_workflow_payload(raw_data: object, model_id: str) -> dict[str, object]:
        if not isinstance(raw_data, dict):
            raise FWExecutionError("Framework build returned invalid payload.")

        if isinstance(raw_data.get("steps"), list):
            return raw_data

        model_payload = raw_data.get(model_id)
        if isinstance(model_payload, dict):
            return model_payload

        if len(raw_data) == 1:
            only_value = next(iter(raw_data.values()))
            if isinstance(only_value, dict):
                return only_value

        raise FWExecutionError("Framework build payload does not contain workflow model.")

    def _run_workflow_build_via_cli(
        self,
        project_path: Path,
        project_id: str,
        model_id: str,
        context: str | None,
    ) -> dict[str, object]:
        build_id = f"wf-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        relative_output = Path(".dqcr_workflow_cache") / f"{model_id}.json"
        absolute_output = project_path / relative_output
        absolute_output.parent.mkdir(parents=True, exist_ok=True)

        args = ["build", str(project_path), model_id, "-o", str(absolute_output)]
        if context and context.strip():
            args.extend(["-c", context.strip()])

        completed = self._run_cli_command(args)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            details = stderr or stdout or f"Framework CLI exited with code {completed.returncode}."
            raise FWExecutionError(f"Framework build failed: {details}")

        if not absolute_output.exists() or not absolute_output.is_file():
            raise FWExecutionError(f"Framework build finished without workflow JSON: {absolute_output}")

        raw_data = json.loads(absolute_output.read_text(encoding="utf-8"))
        workflow_payload = self._normalize_workflow_payload(raw_data, model_id)

        return {
            "build_id": build_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project_id,
            "model": model_id,
            "context": context,
            "workflow_path": str(relative_output),
            "workflow": workflow_payload,
            "execution_mode": "framework_cli",
        }

    def load_project(self, project_id: str) -> Path:
        try:
            return resolve_project_path(self._projects_base_path, project_id)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise FWNotFoundError(str(exc.detail)) from exc
            raise FWValidationError(str(exc.detail)) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise FWExecutionError(f"Failed to load project '{project_id}': {exc}") from exc

    def load_model(self, project_id: str, model_id: str) -> Path:
        project_path = self.load_project(project_id)
        try:
            return self._model_loader(project_path, model_id)
        except ValueError as exc:
            raise FWNotFoundError(str(exc)) from exc
        except HTTPException as exc:
            if exc.status_code == 404:
                raise FWNotFoundError(str(exc.detail)) from exc
            raise FWValidationError(str(exc.detail)) from exc
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise FWExecutionError(f"Failed to load model '{model_id}': {exc}") from exc

    def get_lineage(self, project_id: str, model_id: str) -> dict[str, object]:
        project_path = self.load_project(project_id)
        _ = self.load_model(project_id, model_id)
        try:
            nodes, params_count = self._lineage_nodes_builder(project_path, model_id)
            edges = self._lineage_edges_builder(nodes)
        except Exception as exc:
            raise FWExecutionError(f"Failed to build lineage: {exc}") from exc

        return {
            "project_id": project_id,
            "model_id": model_id,
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "folders": len(nodes),
                "queries": sum(len(node["queries"]) for node in nodes),
                "params": params_count,
            },
        }

    def run_validation(
        self,
        project_id: str,
        model_id: str,
        rules: list[str] | None = None,
    ) -> dict[str, object]:
        project_path = self.load_project(project_id)
        _ = self.load_model(project_id, model_id)
        try:
            if self._prefer_cli and self._cli_available():
                return self._run_validation_via_cli(project_path, project_id, model_id, rules)
            return self._validation_runner(project_path, project_id, model_id, rules)
        except Exception as exc:
            raise FWExecutionError(f"Failed to run validation: {exc}") from exc

    def run_generation(
        self,
        project_id: str,
        model_id: str,
        engine: str,
        context: str,
        dry_run: bool = False,
        output_path: str | None = None,
    ) -> dict[str, object]:
        project_path = self.load_project(project_id)
        _ = self.load_model(project_id, model_id)
        try:
            if self._prefer_cli and not dry_run and self._cli_available():
                return self._run_generation_via_cli(project_path, project_id, model_id, engine, context, output_path)
            return self._generation_runner(project_path, project_id, model_id, engine, context, dry_run, output_path)
        except Exception as exc:
            raise FWExecutionError(f"Failed to run generation: {exc}") from exc

    def run_workflow_build(
        self,
        project_id: str,
        model_id: str,
        context: str | None = None,
    ) -> dict[str, object]:
        project_path = self.load_project(project_id)
        _ = self.load_model(project_id, model_id)
        try:
            if self._prefer_cli and self._cli_available():
                return self._run_workflow_build_via_cli(project_path, project_id, model_id, context)
            raise FWExecutionError("Framework CLI is unavailable for workflow build.")
        except Exception as exc:
            raise FWExecutionError(f"Failed to run workflow build: {exc}") from exc
