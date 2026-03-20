from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.fw_service import FWExecutionError, FWNotFoundError, FWService


def test_load_project_maps_404_to_fw_not_found(tmp_path: Path) -> None:
    service = FWService(
        projects_base_path=tmp_path,
        model_loader=lambda _project_path, _model_id: tmp_path,
        lineage_nodes_builder=lambda _project_path, _model_id: ([], 0),
        lineage_edges_builder=lambda _nodes: [],
        validation_runner=lambda _project_path, _project_id, _model_id, _rules: {},
        generation_runner=lambda _project_path, _project_id, _model_id, _engine, _context, _dry_run, _output_path: {},
    )

    with pytest.raises(FWNotFoundError):
        service.load_project("missing-project")


def test_load_model_maps_value_error_to_fw_not_found(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)

    service = FWService(
        projects_base_path=tmp_path,
        model_loader=lambda _project_path, _model_id: (_ for _ in ()).throw(ValueError("Model not found")),
        lineage_nodes_builder=lambda _project_path, _model_id: ([], 0),
        lineage_edges_builder=lambda _nodes: [],
        validation_runner=lambda _project_path, _project_id, _model_id, _rules: {},
        generation_runner=lambda _project_path, _project_id, _model_id, _engine, _context, _dry_run, _output_path: {},
    )

    with pytest.raises(FWNotFoundError):
        service.load_model("demo", "SampleModel")


def test_get_lineage_returns_summary(tmp_path: Path) -> None:
    (tmp_path / "demo").mkdir(parents=True, exist_ok=True)

    def model_loader(project_path: Path, _model_id: str) -> Path:
        return project_path / "model" / "SampleModel"

    service = FWService(
        projects_base_path=tmp_path,
        model_loader=model_loader,
        lineage_nodes_builder=lambda _project_path, _model_id: (
            [{"id": "a", "queries": ["001.sql"]}, {"id": "b", "queries": ["002.sql", "003.sql"]}],
            4,
        ),
        lineage_edges_builder=lambda _nodes: [{"id": "a->b", "source": "a", "target": "b", "status": "resolved"}],
        validation_runner=lambda _project_path, _project_id, _model_id, _rules: {},
        generation_runner=lambda _project_path, _project_id, _model_id, _engine, _context, _dry_run, _output_path: {},
    )

    result = service.get_lineage("demo", "SampleModel")
    assert result["summary"] == {"folders": 2, "queries": 3, "params": 4}


def test_run_generation_wraps_exception(tmp_path: Path) -> None:
    (tmp_path / "demo").mkdir(parents=True, exist_ok=True)

    service = FWService(
        projects_base_path=tmp_path,
        model_loader=lambda project_path, _model_id: project_path,
        lineage_nodes_builder=lambda _project_path, _model_id: ([], 0),
        lineage_edges_builder=lambda _nodes: [],
        validation_runner=lambda _project_path, _project_id, _model_id, _rules: {},
        generation_runner=lambda _project_path, _project_id, _model_id, _engine, _context, _dry_run, _output_path: (_ for _ in ()).throw(
            HTTPException(status_code=500, detail="boom")
        ),
    )

    with pytest.raises(FWExecutionError):
        service.run_generation("demo", "SampleModel", "dqcr", "default", False, None)

