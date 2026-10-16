from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.coupon import CouponTemplate, DiscountType
from app.models.merchant import Merchant, Sector
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.reel import (
    CouponFeedSummary,
    MerchantFeedSummary,
    ReelCreateRequest,
    ReelOut,
)
from app.utils.geo import calculate_haversine_distance

router = APIRouter()

# Hard sector validity ceilings
SECTOR_VALIDITY_LIMITS = {
    Sector.FOOD: 5,
    Sector.FASHION: 15,
    Sector.FOOTWEAR: 15,
    Sector.ELECTRONICS: 15,
    Sector.REAL_ESTATE: 60,
}


@router.get("/reels/feed", response_model=ResponseEnvelope[List[ReelOut]])
@router.get("/reels", response_model=ResponseEnvelope[List[ReelOut]])
async def get_proximity_feed(
    lat: float = Query(21.1458, ge=-90.0, le=90.0),
    lon: float = Query(79.0882, ge=-180.0, le=180.0),
    radius_km: int = Query(10, ge=1, le=50),
    sector: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):

    """
    Returns proximity-filtered 9:16 vertical reels within the given radius (2km, 5km, 10km).
    Sorted by distance ascending.
    """
    stmt = (
        select(Reel)
        .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        .where(Reel.status == ReelStatus.APPROVED)
        .where(Reel.deleted_at.is_(None))
        .order_by(Reel.created_at.desc())
    )

    result = await db.execute(stmt)
    reels = result.scalars().all()

    feed_items = []
    radius_meters = radius_km * 1000

    for reel in reels:
        merchant = reel.merchant
        if not merchant:
            continue

        merchant_sector = merchant.sector.value if hasattr(merchant.sector, "value") else str(merchant.sector)

        # Optional sector filter
        if sector and merchant_sector != sector.upper():
            continue

        distance_m = calculate_haversine_distance(
            lat, lon, merchant.latitude, merchant.longitude
        )

        if distance_m <= radius_meters:
            coupon_summary = None
            if reel.coupon_template and reel.coupon_template.is_active:
                ct = reel.coupon_template
                d_type = ct.discount_type.value if hasattr(ct.discount_type, "value") else str(ct.discount_type)
                coupon_summary = CouponFeedSummary(
                    id=ct.id,
                    title=ct.title,
                    discount_type=d_type,
                    discount_value=float(ct.discount_value),
                    min_order_amount=float(ct.min_order_amount),
                    validity_days=ct.validity_days
                )

            item = ReelOut(
                id=reel.id,
                title=reel.title,
                video_url=reel.video_url,
                thumbnail_url=reel.thumbnail_url,
                duration_seconds=reel.duration_seconds,
                views_count=reel.views_count,
                merchant=MerchantFeedSummary(
                    id=merchant.id,
                    business_name=merchant.business_name,
                    sector=merchant_sector,
                    address=merchant.address_text,
                    distance_meters=distance_m
                ),
                coupon=coupon_summary
            )
            feed_items.append((distance_m, item))

    # Sort by distance ascending
    feed_items.sort(key=lambda x: x[0])
    sorted_reels = [item for _, item in feed_items[:limit]]

    return ResponseEnvelope(data=sorted_reels)


@router.post("/reels", response_model=ResponseEnvelope[dict])
async def create_reel(
    request: ReelCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a new reel with an attached coupon.
    Enforces sector validity limits and queues reel for Admin moderation.
    """
    res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = res.scalars().first()
    if not merchant:
        # Try matching by phone
        res_phone = await db.execute(
            select(Merchant).join(User, Merchant.user_id == User.id).where(User.phone == current_user.phone)
        )
        merchant = res_phone.scalars().first()

    if not merchant:
        # Development / demo fallback: use primary registered merchant
        res_first = await db.execute(select(Merchant).order_by(Merchant.created_at.asc()).limit(1))
        merchant = res_first.scalars().first()

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please register your store profile before publishing showcase reels."
        )

    # Sector validity check
    max_days = SECTOR_VALIDITY_LIMITS.get(merchant.sector, 15)
    validity_days = min(request.coupon.validity_days, max_days)

    try:
        audio_enum = AudioType(request.audio_type)
    except Exception:
        audio_enum = AudioType.CAMERA_MIC

    try:
        disc_enum = DiscountType(request.coupon.discount_type)
    except Exception:
        disc_enum = DiscountType.PERCENTAGE

    reel = Reel(
        merchant_id=merchant.id,
        title=request.title,
        duration_seconds=request.duration_seconds,
        video_url=request.video_url,
        thumbnail_url=request.thumbnail_url or "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80",
        cloudinary_public_id=request.cloudinary_public_id,
        audio_type=audio_enum,
        status=ReelStatus.PENDING_MODERATION
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
        terms=request.coupon.terms or "Valid for in-store redemption today"
    )
    db.add(coupon)
    await db.flush()

    r_status = reel.status.value if hasattr(reel.status, "value") else str(reel.status)
    return ResponseEnvelope(
        data={"reel_id": str(reel.id), "status": r_status},
        message="Reel created and submitted for admin review."
    )
