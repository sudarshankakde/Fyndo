"""Reel publishing (owner or permitted cashier) and offer-validity management."""
import uuid
from dataclasses import dataclass
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import AuthContext, get_auth_context, get_current_user
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.models.coupon import CouponTemplate, DiscountType
from app.models.merchant import Merchant, MerchantStaff
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.reel import (
    ReelCreateRequest,
    ReelExtendRequest,
    ReelExtendResponse,
    ReelManagementOut,
)
from app.services.reel_lifecycle_service import (
    OfferExtensionError,
    extend_offer,
    max_validity_days,
    start_offer_clock,
    utcnow,
)
from app.services.settings_service import is_auto_approve_enabled

router = APIRouter()


@dataclass
class ReelUploader:
    merchant: Merchant
    actor_id: uuid.UUID
    actor_role: str
    staff: Optional[MerchantStaff] = None


def _is_approved_kyc(merchant: Merchant) -> bool:
    return str(getattr(merchant.kyc_status, "value", merchant.kyc_status)) == "APPROVED"


async def _merchant_for(db: AsyncSession, user: User) -> Optional[Merchant]:
    result = await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    return result.scalars().first()


async def get_reel_uploader(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> ReelUploader:
    """Store owner, or a cashier the owner has allowed to upload reels."""
    if auth.role == "ROLE_CASHIER":
        staff = await db.get(MerchantStaff, auth.subject_id)
        claimed_merchant = str(auth.claims.get("merchant_id", ""))
        if not staff or not staff.is_active or str(staff.merchant_id) != claimed_merchant:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff session is no longer valid.")
        if not staff.can_upload_reels:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ask the store owner to allow you to upload reels.",
            )
        merchant = await db.get(Merchant, staff.merchant_id)
        return ReelUploader(merchant=merchant, actor_id=staff.id, actor_role="ROLE_CASHIER", staff=staff)

    user = await db.get(User, auth.subject_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found or suspended.")
    merchant = await _merchant_for(db, user)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please register your store profile before publishing showcase reels.",
        )
    return ReelUploader(merchant=merchant, actor_id=user.id, actor_role=auth.role)


@router.post("/reels", response_model=ResponseEnvelope[dict])
async def create_reel(
    request: ReelCreateRequest,
    uploader: ReelUploader = Depends(get_reel_uploader),
    db: AsyncSession = Depends(get_db),
):
    """Creates a reel with its coupon; goes live instantly when auto-approve is on."""
    merchant = uploader.merchant
    if not _is_approved_kyc(merchant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your merchant KYC must be approved before publishing reels.",
        )

    thumbnail_url = request.thumbnail_url or settings.DEFAULT_REEL_THUMBNAIL_URL
    if not thumbnail_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A thumbnail image is required for every reel.",
        )

    validity_days = min(request.coupon.validity_days, max_validity_days(merchant.sector))
    try:
        audio_enum = AudioType(request.audio_type)
    except ValueError:
        audio_enum = AudioType.CAMERA_MIC
    try:
        disc_enum = DiscountType(request.coupon.discount_type)
    except ValueError:
        disc_enum = DiscountType.PERCENTAGE

    auto_approve = await is_auto_approve_enabled(db)
    reel = Reel(
        merchant_id=merchant.id,
        title=request.title,
        duration_seconds=request.duration_seconds,
        video_url=request.video_url,
        thumbnail_url=thumbnail_url,
        cloudinary_public_id=request.cloudinary_public_id,
        audio_type=audio_enum,
        allow_comments=request.allow_comments,
        status=ReelStatus.APPROVED if auto_approve else ReelStatus.PENDING_MODERATION,
        created_by_staff_id=uploader.staff.id if uploader.staff else None,
    )
    db.add(reel)
    await db.flush()

    coupon = CouponTemplate(
        merchant_id=merchant.id,
        reel_id=reel.id,
        title=request.coupon.title,
        discount_type=disc_enum,
        discount_value=request.coupon.discount_value,
        min_order_amount=request.coupon.min_order_amount,
        validity_days=validity_days,
        terms=request.coupon.terms or "Valid for in-store redemption today",
    )
    db.add(coupon)
    if auto_approve:
        start_offer_clock(reel, coupon)
    await db.flush()

    audit_log(
        "reel.create",
        actor_id=uploader.actor_id,
        actor_role=uploader.actor_role,
        target_type="reel",
        target_id=reel.id,
        merchant_id=merchant.id,
        auto_approved=auto_approve,
    )
    reel_status = getattr(reel.status, "value", str(reel.status))
    message = "Reel is live for shoppers." if auto_approve else "Reel created and submitted for admin review."
    return ResponseEnvelope(data={"reel_id": str(reel.id), "status": reel_status}, message=message)


@router.post("/reels/{reel_id}/extend-validity", response_model=ResponseEnvelope[ReelExtendResponse])
async def extend_reel_validity(
    reel_id: uuid.UUID,
    request: ReelExtendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner extends an offer, either before it ends or within the 24-hour grace window."""
    merchant = await _merchant_for(db, current_user)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only store owners can extend offers.")
    reel = (
        await db.execute(
            select(Reel)
            .options(selectinload(Reel.coupon_template))
            .where(Reel.id == reel_id, Reel.merchant_id == merchant.id)
        )
    ).scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    try:
        extend_offer(reel, reel.coupon_template, request.additional_days, merchant.sector)
    except OfferExtensionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    await db.flush()
    return ResponseEnvelope(
        data=ReelExtendResponse(
            reel_id=reel.id, expires_at=reel.expires_at, grace_period_until=reel.grace_period_until
        ),
        message="Offer extended.",
    )


@router.get("/merchants/me/reels/expiring", response_model=ResponseEnvelope[List[ReelManagementOut]])
async def list_expiring_reels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reels whose offer has ended and that will be removed unless extended."""
    merchant = await _merchant_for(db, current_user)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found.")
    now = utcnow()
    reels = (
        await db.execute(
            select(Reel)
            .where(
                Reel.merchant_id == merchant.id,
                Reel.deleted_at.is_(None),
                Reel.expires_at <= now,
                Reel.grace_period_until > now,
            )
            .order_by(Reel.grace_period_until.asc())
        )
    ).scalars().all()
    items = []
    for reel in reels:
        out = ReelManagementOut.model_validate(reel)
        out.status = getattr(reel.status, "value", str(reel.status))
        out.is_expired = True
        items.append(out)
    return ResponseEnvelope(data=items)
