import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models.coupon import CouponTemplate, DiscountType
from app.models.merchant import Merchant, Sector
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.reel import (
    CouponFeedSummary,
    MerchantFeedSummary,
    ReelCreateRequest,
    ReelManagementOut,
    ReelOut,
    ReelUpdateRequest,
)
from app.services.reel_feed_service import build_feed

router = APIRouter()

# Hard sector validity ceilings (docs/AGENTS.md section 2)
SECTOR_VALIDITY_LIMITS = {
    Sector.FOOD: 5,
    Sector.FASHION: 15,
    Sector.FOOTWEAR: 15,
    Sector.ELECTRONICS: 15,
    Sector.REAL_ESTATE: 60,
}


async def _merchant_for(db: AsyncSession, user: User) -> Merchant | None:
    result = await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    return result.scalars().first()


def _is_approved_kyc(merchant: Merchant) -> bool:
    kyc = getattr(merchant.kyc_status, "value", str(merchant.kyc_status))
    return kyc == "APPROVED"


@router.get("/reels/feed", response_model=ResponseEnvelope[list[ReelOut]])
@router.get("/reels", response_model=ResponseEnvelope[list[ReelOut]])
async def get_proximity_feed(
    lat: float = Query(21.1458, ge=-90.0, le=90.0),
    lon: float = Query(79.0882, ge=-180.0, le=180.0),
    radius_km: int = Query(10, ge=1, le=50),
    sector: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    _: None = Depends(rate_limit("feed", settings.FEED_RATE_LIMIT_PER_MIN)),
):
    """Proximity-filtered 9:16 vertical reels, nearest first."""
    try:
        items, next_cursor = await build_feed(
            db,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            sector=sector,
            limit=limit,
            cursor=cursor,
            current_user=current_user,
        )
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid feed cursor."
        )
    return ResponseEnvelope(data=items, meta={"next_cursor": next_cursor})


@router.post("/reels", response_model=ResponseEnvelope[dict])
async def create_reel(
    request: ReelCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submits a new reel with an attached coupon for Admin moderation."""
    merchant = await _merchant_for(db, current_user)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please register your store profile before publishing showcase reels.",
        )
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

    max_days = SECTOR_VALIDITY_LIMITS.get(merchant.sector, 15)
    validity_days = min(request.coupon.validity_days, max_days)

    try:
        audio_enum = AudioType(request.audio_type)
    except ValueError:
        audio_enum = AudioType.CAMERA_MIC
    try:
        disc_enum = DiscountType(request.coupon.discount_type)
    except ValueError:
        disc_enum = DiscountType.PERCENTAGE

    reel = Reel(
        merchant_id=merchant.id,
        title=request.title,
        duration_seconds=request.duration_seconds,
        video_url=request.video_url,
        thumbnail_url=thumbnail_url,
        cloudinary_public_id=request.cloudinary_public_id,
        audio_type=audio_enum,
        allow_comments=request.allow_comments,
        status=ReelStatus.PENDING_MODERATION,
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
    await db.flush()

    reel_status = getattr(reel.status, "value", str(reel.status))
    return ResponseEnvelope(
        data={"reel_id": str(reel.id), "status": reel_status},
        message="Reel created and submitted for admin review.",
    )


@router.get("/reels/mine", response_model=ResponseEnvelope[list[ReelManagementOut]])
async def list_my_reels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant = await _merchant_for(db, current_user)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found."
        )

    reels = (
        await db.execute(
            select(Reel)
            .where(Reel.merchant_id == merchant.id)
            .order_by(Reel.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    items = []
    for reel in reels:
        payload = ReelManagementOut.model_validate(reel)
        payload.status = getattr(reel.status, "value", str(reel.status))
        items.append(payload)
    return ResponseEnvelope(data=items)


@router.get("/reels/{reel_id}", response_model=ResponseEnvelope[ReelOut])
async def get_reel(reel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    reel = (
        await db.execute(
            select(Reel).where(
                Reel.id == reel_id,
                Reel.status == ReelStatus.APPROVED,
                Reel.deleted_at.is_(None),
            )
        )
    ).scalars().first()
    if not reel or not reel.merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    merchant = reel.merchant
    coupon = reel.coupon_template
    coupon_summary = None
    if coupon and coupon.is_active:
        coupon_summary = CouponFeedSummary(
            id=coupon.id,
            title=coupon.title,
            discount_type=getattr(coupon.discount_type, "value", str(coupon.discount_type)),
            discount_value=float(coupon.discount_value),
            min_order_amount=float(coupon.min_order_amount),
            validity_days=coupon.validity_days,
        )

    return ResponseEnvelope(
        data=ReelOut(
            id=reel.id,
            title=reel.title,
            video_url=reel.video_url,
            thumbnail_url=reel.thumbnail_url,
            duration_seconds=reel.duration_seconds,
            views_count=reel.views_count,
            allow_comments=reel.allow_comments,
            merchant=MerchantFeedSummary(
                id=merchant.id,
                business_name=merchant.business_name,
                sector=getattr(merchant.sector, "value", str(merchant.sector)),
                address=merchant.address_text,
                distance_meters=0,
            ),
            coupon=coupon_summary,
        )
    )


@router.patch("/reels/{reel_id}", response_model=ResponseEnvelope[ReelManagementOut])
async def update_reel(
    reel_id: uuid.UUID,
    request: ReelUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant = await _merchant_for(db, current_user)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can update reels."
        )
    reel = (
        await db.execute(
            select(Reel).where(Reel.id == reel_id, Reel.merchant_id == merchant.id)
        )
    ).scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    if reel.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Reel has been deactivated."
        )

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(reel, field, value)
    await db.flush()
    await db.refresh(reel)
    payload = ReelManagementOut.model_validate(reel)
    payload.status = getattr(reel.status, "value", str(reel.status))
    return ResponseEnvelope(data=payload, message="Reel updated successfully.")


@router.delete("/reels/{reel_id}", response_model=ResponseEnvelope[dict])
async def delete_reel(
    reel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant = await _merchant_for(db, current_user)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can delete reels."
        )
    reel = (
        await db.execute(
            select(Reel).where(Reel.id == reel_id, Reel.merchant_id == merchant.id)
        )
    ).scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    if not reel.deleted_at:
        reel.deleted_at = datetime.now(timezone.utc)
        await db.flush()
    return ResponseEnvelope(
        data={"reel_id": str(reel.id), "deleted": True}, message="Reel deactivated."
    )
