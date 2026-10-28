"""Reel publishing (owner or permitted cashier) and offer-validity management."""
import uuid
from dataclasses import dataclass
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import AuthContext, get_auth_context, get_current_user, get_merchant_scope, MerchantScope
from app.api.v1.endpoints.merchant_context import MerchantContext, get_merchant_context
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.models.coupon import CouponTemplate, DiscountType
from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.reel import (
    CouponFeedSummary,
    ReelCreateRequest,
    ReelExtendRequest,
    ReelExtendResponse,
    ReelManagementOut,
)
from app.services.cloudinary_service import CloudinaryService
from app.services.merchant_engagement_service import coupon_counts_for_templates
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
    if settings.ENVIRONMENT == "development":
        return True
    return str(getattr(merchant.kyc_status, "value", merchant.kyc_status)) == "APPROVED"


async def _merchant_for(db: AsyncSession, user: User) -> Optional[Merchant]:
    result = await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    merchant = result.scalars().first()
    if not merchant and settings.ENVIRONMENT == "development":
        merchant = Merchant(
            user_id=user.id,
            business_name=user.full_name or "My Store",
            sector=Sector.FOOD,
            address_text="Koramangala, Bengaluru",
            city="Bengaluru",
            kyc_status=KycStatus.APPROVED,
            latitude=12.9352,
            longitude=77.6245,
        )
        db.add(merchant)
        await db.flush()
    return merchant


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
        if not staff.can_upload_reels and not getattr(staff, "can_manage_content", False):
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
    video_url = CloudinaryService.get_optimized_video_url(request.video_url) or request.video_url
    video_hls_url = CloudinaryService.get_hls_url(
        public_id=request.cloudinary_public_id,
        video_url=request.video_url,
    )
    reel = Reel(
        merchant_id=merchant.id,
        title=request.title,
        duration_seconds=request.duration_seconds,
        video_url=video_url,
        video_hls_url=video_hls_url,
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
    ctx: MerchantContext = Depends(get_merchant_context),
    db: AsyncSession = Depends(get_db),
):
    """Owner or authorized content manager extends an offer."""
    if ctx.is_staff and not ctx.can_manage_content:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission 'Manage Content' required.")
    merchant = ctx.merchant
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
    scope: MerchantScope = Depends(get_merchant_scope),
    db: AsyncSession = Depends(get_db),
):
    """Reels whose offer has ended and that will be removed unless extended."""
    now = utcnow()
    reels = (
        await db.execute(
            select(Reel)
            .where(
                Reel.merchant_id == scope.merchant_id,
                Reel.deleted_at.is_(None),
                Reel.expires_at <= now,
                Reel.grace_period_until > now,
            )
            .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
            .order_by(Reel.grace_period_until.asc())
        )
    ).scalars().all()

    template_ids = [r.coupon_template.id for r in reels if r.coupon_template]
    counts_map = await coupon_counts_for_templates(db, template_ids)

    items = []
    for reel in reels:
        out = ReelManagementOut.model_validate(reel)
        out.status = getattr(reel.status, "value", str(reel.status))
        out.is_expired = True
        if reel.merchant:
            out.merchant_name = reel.merchant.business_name
            out.sector = getattr(reel.merchant.sector, "value", str(reel.merchant.sector))
            out.city = reel.merchant.city
            out.is_verified = bool(reel.merchant.kyc_status == KycStatus.APPROVED)
        coupon = reel.coupon_template
        if coupon:
            claims, redemptions = counts_map.get(coupon.id, (0, 0))
            out.claims_count = claims
            out.redemptions_count = redemptions
            if coupon.is_active:
                out.coupon = CouponFeedSummary(
                    id=coupon.id,
                    title=coupon.title,
                    discount_type=getattr(coupon.discount_type, "value", str(coupon.discount_type)),
                    discount_value=float(coupon.discount_value),
                    min_order_amount=float(coupon.min_order_amount),
                    validity_days=coupon.validity_days,
                    expires_at=coupon.expires_at,
                    terms=coupon.terms,
                )
        items.append(out)
    return ResponseEnvelope(data=items)
