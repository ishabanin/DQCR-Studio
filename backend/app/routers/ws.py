from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.services.terminal_service import TerminalService
from app.routers.projects import (
    FW_SERVICE,
    _attach_workflow_context,
    _build_validation_result,
    _record_build_result,
    _resolve_model_id_for_validation,
)
from app.core.fs import resolve_project_path

router = APIRouter(prefix="/ws", tags=["ws"])
terminal_service = TerminalService()


@router.websocket("/terminal/{session_id}")
async def ws_terminal(session_id: str, websocket: WebSocket):
    await websocket.accept()
    terminal_service.create_session(session_id, Path(settings.projects_path))

    async def stream_output() -> None:
        while True:
            output = terminal_service.read_nonblocking(session_id)
            if output:
                await websocket.send_text(output)
            await asyncio.sleep(0.05)

    stream_task = asyncio.create_task(stream_output())

    try:
        while True:
            message = await websocket.receive_text()
            if message:
                terminal_service.write(session_id, message)
    except WebSocketDisconnect:
        terminal_service.close_session(session_id)
    finally:
        stream_task.cancel()


@router.websocket("/validation/{project_id}")
async def ws_validation(project_id: str, websocket: WebSocket):
    await websocket.accept()
    try:
        payload_raw = await websocket.receive_text()
        payload = json.loads(payload_raw) if payload_raw else {}
        model_id_raw = payload.get("model_id") if isinstance(payload, dict) else None
        categories_raw = payload.get("categories") if isinstance(payload, dict) else None
        model_id = model_id_raw if isinstance(model_id_raw, str) else None
        categories = categories_raw if isinstance(categories_raw, list) else None

        await websocket.send_json({"type": "progress", "percent": 10, "stage": "queued"})
        await asyncio.sleep(0.1)
        await websocket.send_json({"type": "progress", "percent": 35, "stage": "loading_project"})
        await asyncio.sleep(0.1)
        await websocket.send_json({"type": "progress", "percent": 70, "stage": "running_rules"})

        base_projects = Path(settings.projects_path)
        project_path = resolve_project_path(base_projects, project_id)
        resolved_model_id = _resolve_model_id_for_validation(project_path, model_id)
        result = _build_validation_result(project_path, project_id, resolved_model_id, categories)

        await asyncio.sleep(0.1)
        await websocket.send_json({"type": "progress", "percent": 100, "stage": "completed"})
        await websocket.send_json({"type": "done", "result": result})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        await websocket.close()


@router.websocket("/build/{project_id}")
async def ws_build(project_id: str, websocket: WebSocket):
    await websocket.accept()
    try:
        payload_raw = await websocket.receive_text()
        payload = json.loads(payload_raw) if payload_raw else {}
        model_id_raw = payload.get("model_id") if isinstance(payload, dict) else None
        engine_raw = payload.get("engine") if isinstance(payload, dict) else None
        context_raw = payload.get("context") if isinstance(payload, dict) else None
        dry_run_raw = payload.get("dry_run") if isinstance(payload, dict) else None
        output_path_raw = payload.get("output_path") if isinstance(payload, dict) else None

        model_id_input = model_id_raw if isinstance(model_id_raw, str) and model_id_raw.strip() else None
        engine = engine_raw.strip() if isinstance(engine_raw, str) and engine_raw.strip() else "dqcr"
        context = context_raw.strip() if isinstance(context_raw, str) and context_raw.strip() else "default"
        dry_run = bool(dry_run_raw) if dry_run_raw is not None else False
        output_path = output_path_raw.strip() if isinstance(output_path_raw, str) and output_path_raw.strip() else None

        await websocket.send_json({"type": "progress", "percent": 8, "stage": "queued"})
        await asyncio.sleep(0.1)
        await websocket.send_json({"type": "progress", "percent": 24, "stage": "loading_project"})

        project_path = FW_SERVICE.load_project(project_id)
        model_id = _resolve_model_id_for_validation(project_path, model_id_input)

        await asyncio.sleep(0.1)
        await websocket.send_json({"type": "progress", "percent": 58, "stage": "rendering_sql"})
        result = FW_SERVICE.run_generation(
            project_id=project_id,
            model_id=model_id,
            engine=engine,
            context=context,
            dry_run=dry_run,
            output_path=output_path,
        )
        result = _attach_workflow_context(result, project_path, model_id)
        _record_build_result(project_id, result)

        await asyncio.sleep(0.1)
        await websocket.send_json({"type": "progress", "percent": 100, "stage": "completed"})
        await websocket.send_json({"type": "done", "result": result})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        await websocket.close()
