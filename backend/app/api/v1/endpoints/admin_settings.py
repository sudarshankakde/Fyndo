"""Super Admin platform settings (e.g. the reel auto-approve switch)."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin import get_current_admin
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.system_settings import AUTO_APPROVE_KYC, AUTO_APPROVE_REELS
from app.models.user import User
from app.schemas.admin import SystemSettingOut, SystemSettingsUpdateRequest
from app.schemas.common import ResponseEnvelope
from app.services import settings_service

router = APIRouter()


@router.get("/admin/settings", response_model=ResponseEnvelope[List[SystemSettingOut]])
async def get_system_settings(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await settings_service.list_settings(db)
    return ResponseEnvelope(data=[SystemSettingOut(**item) for item in items])


@router.patch("/admin/settings", response_model=ResponseEnvelope[List[SystemSettingOut]])
@router.put("/admin/settings", response_model=ResponseEnvelope[List[SystemSettingOut]])
async def update_system_settings(
    payload: SystemSettingsUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.auto_approve_reels is not None:
        await settings_service.set_setting(
            db, AUTO_APPROVE_REELS, payload.auto_approve_reels, updated_by=admin.id
        )
        audit_log(
            "system_settings.update",
            actor_id=admin.id,
            actor_role="SUPER_ADMIN",
            target_type="system_settings",
            target_id=AUTO_APPROVE_REELS,
            value=payload.auto_approve_reels,
        )
    if payload.auto_approve_kyc is not None:
        await settings_service.set_setting(
            db, AUTO_APPROVE_KYC, payload.auto_approve_kyc, updated_by=admin.id
        )
        audit_log(
            "system_settings.update",
            actor_id=admin.id,
            actor_role="SUPER_ADMIN",
            target_type="system_settings",
            target_id=AUTO_APPROVE_KYC,
            value=payload.auto_approve_kyc,
        )
    items = await settings_service.list_settings(db)
    return ResponseEnvelope(data=[SystemSettingOut(**item) for item in items], message="Settings saved.")
