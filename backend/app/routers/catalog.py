from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.services.catalog_service import CatalogService


router = APIRouter(prefix="/catalog", tags=["catalog"])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_ALLOWED_XLSX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


def _catalog_service() -> CatalogService:
    return CatalogService(Path(settings.catalog_path))


@router.get("")
def get_catalog_status() -> dict[str, object]:
    service = _catalog_service()
    meta = service.load_meta()
    available = service.is_available() and meta is not None
    return {
        "available": available,
        "meta": meta.model_dump() if meta is not None else None,
    }


@router.post("/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    version_label: str = Form(default=""),
) -> dict[str, object]:
    filename = (file.filename or "").strip()
    content_type = (file.content_type or "").strip().lower()

    if not filename.lower().endswith(".xlsx") or content_type not in _ALLOWED_XLSX_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only .xlsx files are supported.",
        )

    payload = await file.read()
    if len(payload) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Catalog file is too large (max 50 MB).",
        )

    service = _catalog_service()
    try:
        entities, meta = service.parse_xlsx(payload, filename=filename, version_label=version_label.strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    service.save(entities, meta)
    return {
        "available": True,
        "meta": meta.model_dump(),
    }


@router.get("/entities")
def get_catalog_entities(
    search: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    service = _catalog_service()
    if not service.is_available():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not loaded")

    entities, total = service.search_entities_with_total(query=search, limit=limit)

    return {
        "entities": entities,
        "total": total,
    }


@router.get("/entities/{entity_name}")
def get_catalog_entity(entity_name: str) -> dict[str, object]:
    service = _catalog_service()
    if not service.is_available():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not loaded")

    entity = service.get_entity(entity_name)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entity '{entity_name}' not found")

    return entity.model_dump()
