"""Assembles the ``/admin`` router: assets first, then auth, then custom views, then generic CRUD."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.admin.analytics_views import router as analytics_views_router
from app.admin.audit_views import router as audit_views_router
from app.admin.auth import router as auth_router
from app.admin.crud import router as crud_router
from app.admin.kyc_views import router as kyc_views_router
from app.admin.merchant_views import router as merchant_views_router
from app.admin.moderation_views import router as moderation_views_router
from app.admin.notification_views import router as notification_views_router
from app.admin.settings_views import router as settings_views_router
from app.admin.subscription_views import router as subscription_views_router
from app.admin.templating import STATIC_DIR
from app.admin.user_views import router as user_views_router
from app.admin.views import router as views_router

admin_router = APIRouter(prefix="/admin", include_in_schema=False, tags=["admin-panel"])


@admin_router.get("/static/{filename}", include_in_schema=False)
async def admin_static(filename: str) -> FileResponse:
    """Serves the panel's CSS/JS."""
    target = (STATIC_DIR / Path(filename).name).resolve()
    if not target.is_file() or STATIC_DIR.resolve() not in target.parents:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(target)


# Inclusion order strictly ensures specific endpoints are matched ahead of catch-all CRUD routes:
admin_router.include_router(auth_router)
admin_router.include_router(merchant_views_router)
admin_router.include_router(moderation_views_router)
admin_router.include_router(subscription_views_router)
admin_router.include_router(kyc_views_router)
admin_router.include_router(user_views_router)
admin_router.include_router(settings_views_router)
admin_router.include_router(audit_views_router)
admin_router.include_router(analytics_views_router)
admin_router.include_router(notification_views_router)
admin_router.include_router(views_router)
admin_router.include_router(crud_router)
