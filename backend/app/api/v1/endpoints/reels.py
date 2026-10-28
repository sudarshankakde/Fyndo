import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.auth import get_current_user, get_merchant_scope, get_optional_user, MerchantScope
from app.api.v1.endpoints.merchant_context import MerchantContext, get_merchant_context
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models.merchant import KycStatus, Merchant, MerchantStaff
from app.models.reel import Reel, ReelStatus
from app.models.reel_engagement import ReelComment, ReelLike
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.reel import (
    CouponFeedSummary,
    MerchantFeedSummary,
    ReelManagementOut,
    ReelOut,
    ReelUpdateRequest,
)
from app.services.category_assets import get_default_logo_url
from app.services.cloudinary_service import CloudinaryService
from app.services.merchant_engagement_service import coupon_counts_for_templates
from app.services.reel_feed_service import _count_map, _hydrate_user_likes, build_feed
from app.services.reel_lifecycle_service import as_aware, live_offer_clause, utcnow

router = APIRouter()


async def _merchant_for(db: AsyncSession, user: User) -> Merchant | None:
    result = await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    merchant = result.scalars().first()
    if not merchant and user.phone:
        staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.phone == user.phone))
        staff = staff_res.scalars().first()
        if staff:
            merchant = await db.get(Merchant, staff.merchant_id)
    return merchant


@router.get("/reels/feed", response_model=ResponseEnvelope[list[ReelOut]])
@router.get("/reels", response_model=ResponseEnvelope[list[ReelOut]])
async def get_proximity_feed(
    lat: float = Query(21.1458, ge=-90.0, le=90.0),
    lon: float = Query(79.0882, ge=-180.0, le=180.0),
    radius_km: int = Query(10, ge=1, le=50),
    city: str | None = Query(None),
    sector: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    merchant_id: uuid.UUID | None = Query(None),
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
            city=city,
            sector=sector,
            limit=limit,
            cursor=cursor,
            merchant_id=merchant_id,
            current_user=current_user,
        )
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid feed cursor."
        )
    meta = {
        "next_cursor": next_cursor,
        "serviceable": len(items) > 0,
        "radius_km": radius_km,
    }
    message = (
        f"Found {len(items)} offers near you"
        if items
        else "We don't serve in this area yet. We will be here soon!"
    )
    return ResponseEnvelope(data=items, meta=meta, message=message)


@router.get("/reels/mine", response_model=ResponseEnvelope[list[ReelManagementOut]])
async def list_my_reels(
    scope: MerchantScope = Depends(get_merchant_scope),
    db: AsyncSession = Depends(get_db),
):
    reels = (
        await db.execute(
            select(Reel)
            .where(Reel.merchant_id == scope.merchant_id, Reel.deleted_at.is_(None))
            .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
            .order_by(Reel.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    template_ids = [r.coupon_template.id for r in reels if r.coupon_template]
    counts_map = await coupon_counts_for_templates(db, template_ids)
    reel_ids = [r.id for r in reels]
    like_counts = await _count_map(db, ReelLike, reel_ids)
    comment_counts = await _count_map(db, ReelComment, reel_ids)

    # Map to schema and inject merchant metadata & attached coupon
    reel_list = []
    for reel in reels:
        out = ReelManagementOut.model_validate(reel)
        out.status = getattr(reel.status, "value", str(reel.status))
        out.likes_count = int(like_counts.get(reel.id, 0))
        out.comments_count = int(comment_counts.get(reel.id, 0))
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
        reel_list.append(out)

    return ResponseEnvelope(data=reel_list)


@router.get("/reels/{reel_id}", response_model=ResponseEnvelope[ReelOut])
async def get_reel(
    reel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    merchant = await _merchant_for(db, current_user) if current_user else None

    reel = (
        await db.execute(
            select(Reel)
            .where(
                Reel.id == reel_id,
                Reel.deleted_at.is_(None),
            )
            .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        )
    ).scalars().first()
    if not reel or not reel.merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    is_owner = bool(merchant and reel.merchant_id == merchant.id)
    if not is_owner:
        if reel.status != ReelStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
        now = utcnow()
        exp = as_aware(reel.expires_at)
        if exp and exp <= now:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel has expired.")

    merchant_obj = reel.merchant
    coupon = reel.coupon_template
    coupon_summary = None
    if coupon and (coupon.is_active or is_owner):
        coupon_summary = CouponFeedSummary(
            id=coupon.id,
            title=coupon.title,
            discount_type=getattr(coupon.discount_type, "value", str(coupon.discount_type)),
            discount_value=float(coupon.discount_value),
            min_order_amount=float(coupon.min_order_amount),
            validity_days=coupon.validity_days,
            expires_at=coupon.expires_at,
            terms=coupon.terms,
        )

    v_url = CloudinaryService.get_optimized_video_url(reel.video_url) or reel.video_url
    hls_url = getattr(reel, "video_hls_url", None) or CloudinaryService.get_hls_url(
        public_id=getattr(reel, "cloudinary_public_id", None), video_url=reel.video_url
    )
    merchant_sector = getattr(merchant_obj.sector, "value", str(merchant_obj.sector))
    like_counts = await _count_map(db, ReelLike, [reel.id])
    comment_counts = await _count_map(db, ReelComment, [reel.id])
    out = ReelOut(
        id=reel.id,
        title=reel.title,
        video_url=v_url,
        video_hls_url=hls_url,
        thumbnail_url=reel.thumbnail_url,
        duration_seconds=reel.duration_seconds,
        views_count=reel.views_count,
        likes_count=int(like_counts.get(reel.id, 0)),
        is_liked=False,
        is_bookmarked=False,
        allow_comments=reel.allow_comments,
        comments_count=int(comment_counts.get(reel.id, 0)),
        status=getattr(reel.status, "value", str(reel.status)),
        merchant=MerchantFeedSummary(
            id=merchant_obj.id,
            business_name=merchant_obj.business_name,
            sector=merchant_sector,
            address=merchant_obj.address_text,
            distance_meters=0,
            logo_url=merchant_obj.logo_url or get_default_logo_url(merchant_sector),
            is_verified=bool(merchant_obj.kyc_status == KycStatus.APPROVED),
        ),
        coupon=coupon_summary,
    )
    hydrated = await _hydrate_user_likes(db, [out], current_user)
    return ResponseEnvelope(data=hydrated[0])


@router.patch("/reels/{reel_id}", response_model=ResponseEnvelope[ReelManagementOut])
async def update_reel(
    reel_id: uuid.UUID,
    request: ReelUpdateRequest,
    ctx: MerchantContext = Depends(get_merchant_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.is_staff and not ctx.can_manage_content:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff permission 'Manage Content' is required to update reels."
        )
    merchant = ctx.merchant
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
    ctx: MerchantContext = Depends(get_merchant_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.is_staff and not ctx.can_manage_content:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff permission 'Manage Content' is required to delete reels."
        )
    merchant = ctx.merchant
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
