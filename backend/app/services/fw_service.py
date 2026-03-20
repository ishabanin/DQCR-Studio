from __future__ import annotations

from dataclasses import dataclass
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
    ) -> None:
        self._projects_base_path = projects_base_path
        self._model_loader = model_loader
        self._lineage_nodes_builder = lineage_nodes_builder
        self._lineage_edges_builder = lineage_edges_builder
        self._validation_runner = validation_runner
        self._generation_runner = generation_runner
        self._template_registry = template_registry or TemplateRegistry(
            templates=("dqcr", "airflow", "dbt", "oracle_plsql")
        )

    @property
    def template_registry(self) -> TemplateRegistry:
        return self._template_registry

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
            return self._generation_runner(project_path, project_id, model_id, engine, context, dry_run, output_path)
        except Exception as exc:
            raise FWExecutionError(f"Failed to run generation: {exc}") from exc
