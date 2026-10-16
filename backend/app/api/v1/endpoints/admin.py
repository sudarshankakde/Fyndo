import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.merchant import KycStatus, Merchant
from app.models.reel import Reel, ReelStatus
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminMerchantCreateRequest,
    AdminMerchantDetail,
    AdminMerchantUpdateRequest,
    AdminReelCreateRequest,
    AdminReelListItem,
    AdminReelUpdateRequest,
    AdminStaffUpdateRequest,
    AdminStatsResponse,
    MerchantKycDecisionRequest,
    ModerationDecisionRequest,
)
from app.schemas.common import ResponseEnvelope
from app.services.admin_service import AdminService
from app.services.moderation_alerts import notify_merchant_decision, notify_reel_decision

router = APIRouter()


def _role(role: object) -> str:
    return str(getattr(role, "value", role))


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency verifying Super Admin privileges."""
    role = getattr(current_user.role, "value", current_user.role)
    if str(role).strip().upper() != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required."
        )
    return current_user


@router.get("/admin/stats", response_model=ResponseEnvelope[AdminStatsResponse])
async def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Platform health overview metrics and counts."""
    stats = await AdminService.get_platform_stats(db)
    return ResponseEnvelope(data=stats)


@router.get("/admin/merchants", response_model=ResponseEnvelope[List[AdminMerchantDetail]])
async def list_admin_merchants(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Lists all registered merchants with KYC status, staff and reel counts."""
    merchants = await AdminService.list_merchants(db)
    return ResponseEnvelope(data=merchants)


@router.get("/admin/moderation/merchants")
async def list_merchant_kyc(
    status_filter: Optional[str] = Query(None, alias="status"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Merchant)
        .options(selectinload(Merchant.owner))
        .order_by(Merchant.created_at.asc())
    )
    if status_filter:
        try:
            stmt = stmt.where(Merchant.kyc_status == KycStatus(status_filter.upper()))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid KYC status.")
    merchants = (await db.execute(stmt)).scalars().all()
    return ResponseEnvelope(
        data=[
            {
                "id": merchant.id,
                "business_name": merchant.business_name,
                "sector": merchant.sector.value if hasattr(merchant.sector, "value") else str(merchant.sector),
                "city": merchant.city,
                "kyc_doc_url": merchant.kyc_doc_url,
                "kyc_status": merchant.kyc_status.value if hasattr(merchant.kyc_status, "value") else str(merchant.kyc_status),
                "kyc_rejection_reason": merchant.kyc_rejection_reason,
                "owner_phone": merchant.owner.phone if merchant.owner else "",
                "submitted_at": merchant.created_at,
            }
            for merchant in merchants
        ]
    )


@router.post("/admin/moderation/merchants/{merchant_id}/decision")
async def decide_merchant_kyc(
    merchant_id: uuid.UUID,
    payload: MerchantKycDecisionRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    merchant = (await db.execute(select(Merchant).where(Merchant.id == merchant_id))).scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")

    decision = payload.decision.upper()
    if decision == "APPROVE":
        merchant.kyc_status = KycStatus.APPROVED
        merchant.kyc_rejection_reason = None
        message = "Merchant KYC approved."
    elif decision == "REJECT":
        if not payload.rejection_reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rejection reason is required.")
        merchant.kyc_status = KycStatus.REJECTED
        merchant.kyc_rejection_reason = payload.rejection_reason
        message = "Merchant KYC rejected."
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be 'APPROVE' or 'REJECT'.")

    await db.flush()
    audit_log(
        "merchant.kyc_decision",
        actor_id=admin.id,
        actor_role=_role(admin.role),
        target_type="merchant",
        target_id=merchant.id,
        decision=decision,
        kyc_status=merchant.kyc_status.value,
        rejection_reason=merchant.kyc_rejection_reason,
    )
    await notify_merchant_decision(
        db,
        merchant=merchant,
        decision=decision,
        rejection_reason=payload.rejection_reason,
    )
    return ResponseEnvelope(
        data={
            "merchant_id": str(merchant.id),
            "kyc_status": merchant.kyc_status.value,
            "rejection_reason": merchant.kyc_rejection_reason,
        },
        message=message,
    )


@router.post("/admin/merchants", response_model=ResponseEnvelope[AdminMerchantDetail])
async def create_admin_merchant(
    payload: AdminMerchantCreateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new merchant store directly with associated owner and staff PIN."""
    merchant = await AdminService.create_merchant(payload, db)
    audit_log(
        "merchant.create",
        actor_id=admin.id,
        actor_role=_role(admin.role),
        target_type="merchant",
        target_id=merchant.id,
        business_name=merchant.business_name,
    )
    return ResponseEnvelope(data=merchant, message="Merchant store registered successfully.")


@router.put("/admin/merchants/{merchant_id}", response_model=ResponseEnvelope[dict])
async def update_admin_merchant(
    merchant_id: uuid.UUID,
    payload: AdminMerchantUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Updates merchant parameters (business name, location, address, KYC status)."""
    updated = await AdminService.update_merchant(merchant_id, payload, db)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")
    audit_log(
        "merchant.update",
        actor_id=admin.id,
        actor_role=_role(admin.role),
        target_type="merchant",
        target_id=merchant_id,
        fields=sorted(payload.model_dump(exclude_unset=True).keys()),
    )
    return ResponseEnvelope(data={"merchant_id": str(merchant_id)}, message="Merchant updated successfully.")


@router.put("/admin/merchants/{merchant_id}/staff", response_model=ResponseEnvelope[dict])
async def update_admin_merchant_staff(
    merchant_id: uuid.UUID,
    payload: AdminStaffUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Sets or resets the 6-digit scanner PIN and staff name for a merchant terminal."""
    staff = await AdminService.update_staff_pin(merchant_id, payload, db)
    audit_log(
        "merchant.staff_credentials_update",
        actor_id=admin.id,
        actor_role=_role(admin.role),
        target_type="merchant_staff",
        target_id=staff.id,
        merchant_id=merchant_id,
    )
    return ResponseEnvelope(
        data={"staff_id": str(staff.id), "staff_name": staff.staff_name},
        message="Staff terminal credentials updated successfully."
    )


@router.get("/admin/moderation/reels", response_model=ResponseEnvelope[List[AdminReelListItem]])
async def list_pending_reels(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Lists all reels currently queued in PENDING_MODERATION state."""
    items = await AdminService.list_all_reels(status="PENDING_MODERATION", db=db)
    return ResponseEnvelope(data=items)


@router.post("/admin/moderation/reels/{reel_id}/decision", response_model=ResponseEnvelope[dict])
async def decide_reel_moderation(
    reel_id: uuid.UUID,
    payload: ModerationDecisionRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approves or rejects a reel in moderation queue."""
    stmt = select(Reel).options(selectinload(Reel.merchant)).where(Reel.id == reel_id)
    res = await db.execute(stmt)
    reel = res.scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    decision_norm = payload.decision.upper()
    if decision_norm == "APPROVE":
        reel.status = ReelStatus.APPROVED
        reel.rejection_reason = None
        message = "Reel approved and pushed to live discovery feed."
    elif decision_norm == "REJECT":
        reel.status = ReelStatus.REJECTED
        reel.rejection_reason = payload.rejection_reason or "Violated content or audio guidelines."
        message = "Reel rejected."
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be 'APPROVE' or 'REJECT'.")

    await db.flush()
    status_str = reel.status.value if hasattr(reel.status, "value") else str(reel.status)
    audit_log(
        "reel.moderate",
        actor_id=admin.id,
        actor_role=_role(admin.role),
        target_type="reel",
        target_id=reel.id,
        decision=decision_norm,
        status=status_str,
        rejection_reason=reel.rejection_reason,
    )
    owner_id = reel.merchant.user_id if reel.merchant else None
    await notify_reel_decision(db, reel=reel, owner_id=owner_id, decision=decision_norm)
    return ResponseEnvelope(data={"reel_id": str(reel.id), "status": status_str}, message=message)


@router.get("/admin/reels", response_model=ResponseEnvelope[List[AdminReelListItem]])
async def list_all_reels_admin(
    status: Optional[str] = Query(None, description="ALL, PENDING_MODERATION, APPROVED, REJECTED"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Lists all reels across the platform with optional status filter."""
    items = await AdminService.list_all_reels(status=status, db=db)
    return ResponseEnvelope(data=items)


@router.post("/admin/reels", response_model=ResponseEnvelope[dict])
async def create_admin_reel(
    payload: AdminReelCreateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new approved reel with attached coupon template directly."""
    reel_id = await AdminService.create_reel(payload, db)
    audit_log(
        "reel.create",
        actor_id=admin.id,
        actor_role=_role(admin.role),
        target_type="reel",
        target_id=reel_id,
    )
    return ResponseEnvelope(data={"reel_id": str(reel_id)}, message="Reel and offer published to live feed.")
