from contextlib import asynccontextmanager
import logging
from pathlib import Path
import shutil
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.routers.admin import router as admin_router
from app.routers.catalog import router as catalog_router
from app.routers.files import router as files_router
from app.routers.projects import router as projects_router
from app.routers.ws import router as ws_router
from app.services import FWError

setup_logging(settings.log_level)
logger = logging.getLogger("dqcr.backend")


def _check_writable_directory(path_value: str) -> dict[str, object]:
    path = Path(path_value)
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".dqcr_readiness_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "path": str(path)}
    except OSError as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}


def _build_readiness_payload() -> dict[str, object]:
    checks: dict[str, dict[str, object]] = {
        "projects_path": _check_writable_directory(settings.projects_path),
        "catalog_path": _check_writable_directory(settings.catalog_path),
    }

    if settings.fw_use_cli:
        resolved_cli = shutil.which(settings.fw_cli_command)
        checks["fw_cli"] = {
            "ok": bool(resolved_cli),
            "command": settings.fw_cli_command,
            "resolved_path": resolved_cli,
        }
    else:
        checks["fw_cli"] = {
            "ok": True,
            "command": settings.fw_cli_command,
            "skipped": "fw_use_cli is disabled",
        }

    ready = all(bool(check.get("ok")) for check in checks.values())
    return {"status": "ready" if ready else "not_ready", "checks": checks}


@asynccontextmanager
async def lifespan(app: FastAPI):
    payload = _build_readiness_payload()
    app.state.fw_ready = payload["status"] == "ready"
    app.state.readiness = payload
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(request: Request) -> JSONResponse:
    payload = _build_readiness_payload()
    request.app.state.fw_ready = payload["status"] == "ready"
    request.app.state.readiness = payload
    return JSONResponse(status_code=200 if request.app.state.fw_ready else 503, content=payload)


app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(files_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(catalog_router, prefix=settings.api_prefix)
app.include_router(ws_router)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FWError)
async def fw_error_handler(_: Request, exc: FWError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.code,
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
