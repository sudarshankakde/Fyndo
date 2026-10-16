"""Assembles the ``/admin`` router: assets first, then auth, then the views."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.admin.auth import router as auth_router
from app.admin.crud import router as crud_router
from app.admin.templating import STATIC_DIR
from app.admin.views import router as views_router

admin_router = APIRouter(prefix="/admin", include_in_schema=False, tags=["admin-panel"])


@admin_router.get("/static/{filename}", include_in_schema=False)
async def admin_static(filename: str) -> FileResponse:
    """Serves the panel's CSS/JS.

    A mounted ``StaticFiles`` app would be silently dropped by FastAPI's
    ``include_router`` (it only copies API routes), so the assets are served
    through an explicit route instead. Registered first so that
    ``/admin/static/...`` is never captured by ``/admin/{model_key}/{pk}``.
    """
    target = (STATIC_DIR / Path(filename).name).resolve()
    if not target.is_file() or STATIC_DIR.resolve() not in target.parents:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(target)


# Auth routes come ahead of the generic ``/{model_key}`` routes so that
# ``/admin/login`` and ``/admin/logout`` are never read as table names.
admin_router.include_router(auth_router)
admin_router.include_router(views_router)
admin_router.include_router(crud_router)
