"""Admin panel views and actions for platform-wide settings."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import panel_context, record_audit_log
from app.admin.templating import templates
from app.core.database import get_db
from app.models.system_settings import (
    AUTO_APPROVE_KYC,
    AUTO_APPROVE_REELS,
    AUTO_TRIAL_DURATION_DAYS,
    AUTO_TRIAL_ENABLED,
    MAINTENANCE_MODE,
)
from app.services.settings_service import (
    get_auto_trial_duration_days,
    is_auto_approve_enabled,
    is_auto_approve_kyc_enabled,
    is_auto_trial_enabled,
    is_maintenance_mode_enabled,
    list_settings,
    set_setting,
)

logger = logging.getLogger("fyndo.admin.settings")
router = APIRouter()


@router.get("/settings")
async def settings_view(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Consolidated platform settings page."""
    all_settings = await list_settings(db)
    auto_reels = await is_auto_approve_enabled(db)
    auto_kyc = await is_auto_approve_kyc_enabled(db)
    auto_trial = await is_auto_trial_enabled(db)
    trial_days = await get_auto_trial_duration_days(db)
    maintenance = await is_maintenance_mode_enabled(db)

    return templates.TemplateResponse(
        request,
        "settings.html",
        panel_context(
            request,
            admin,
            settings_list=all_settings,
            auto_approve_reels=auto_reels,
            auto_approve_kyc=auto_kyc,
            auto_trial_enabled=auto_trial,
            auto_trial_duration_days=trial_days,
            maintenance_mode=maintenance,
        ),
    )


@router.post("/settings/auto-trial")
async def update_auto_trial_settings_action(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Updates auto-trial enabled state and default duration."""
    form = await request.form()
    enabled = form.get("enabled") in ("on", "true", "True", "1")
    duration_raw = form.get("duration_days")
    try:
        duration_days = max(1, min(3650, int(duration_raw))) if duration_raw else 90
    except (ValueError, TypeError):
        duration_days = 90

    await set_setting(db, AUTO_TRIAL_ENABLED, enabled)
    await set_setting(db, AUTO_TRIAL_DURATION_DAYS, duration_days)
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="system_settings.update",
        target_type="system_settings",
        target_id="auto_trial",
        details={"enabled": enabled, "duration_days": duration_days},
    )
    await db.commit()

    ref = request.headers.get("referer", "")
    target_url = "/admin/settings?ok=Auto-trial+settings+updated" if "/admin/settings" in ref else f"/admin/?ok=Auto-trial+settings+updated+(Enabled:+{enabled},+Duration:+{duration_days}+days)"
    return RedirectResponse(url=target_url, status_code=303)


@router.post("/settings/auto-approve")
async def toggle_auto_approve(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Toggles automatic reel moderation approval."""
    form = await request.form()
    enabled = form.get("enabled") in ("on", "true", "True", "1")
    await set_setting(db, AUTO_APPROVE_REELS, enabled)
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="system_settings.update",
        target_type="system_settings",
        target_id=AUTO_APPROVE_REELS,
        details={"value": enabled},
    )
    await db.commit()

    ref = request.headers.get("referer", "")
    target_url = "/admin/settings?ok=Auto-reel+approval+updated" if "/admin/settings" in ref else "/admin/"
    return RedirectResponse(target_url, status_code=303)


@router.post("/settings/auto-approve-kyc")
async def toggle_auto_approve_kyc(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Toggles automatic merchant KYC verification."""
    form = await request.form()
    enabled = form.get("enabled") in ("on", "true", "True", "1")
    await set_setting(db, AUTO_APPROVE_KYC, enabled)
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="system_settings.update",
        target_type="system_settings",
        target_id=AUTO_APPROVE_KYC,
        details={"value": enabled},
    )
    await db.commit()

    ref = request.headers.get("referer", "")
    target_url = "/admin/settings?ok=Auto-KYC+approval+updated" if "/admin/settings" in ref else "/admin/"
    return RedirectResponse(target_url, status_code=303)


@router.post("/settings/maintenance-mode")
async def toggle_maintenance_mode(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    """Toggles platform-wide maintenance mode."""
    form = await request.form()
    enabled = form.get("enabled") in ("on", "true", "True", "1")
    await set_setting(db, MAINTENANCE_MODE, enabled)
    await record_audit_log(
        db,
        admin_user=admin.get("sub"),
        action="system_settings.update",
        target_type="system_settings",
        target_id=MAINTENANCE_MODE,
        details={"value": enabled},
    )
    await db.commit()

    msg = "Platform+maintenance+mode+enabled" if enabled else "Maintenance+mode+disabled"
    return RedirectResponse(f"/admin/settings?ok={msg}", status_code=303)
