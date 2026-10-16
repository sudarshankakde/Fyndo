import base64
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.coupon import CouponTemplate, DiscountType
from app.models.merchant import Merchant, Sector
from app.models.reel import AudioType, Reel, ReelStatus, ReelView
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
from app.utils.geo import calculate_haversine_distance

router = APIRouter()
optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload or payload.get("role") == "ROLE_CASHIER":
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        return None
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    return result.scalars().first()

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
    cursor: Optional[str] = Query(None),
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
                allow_comments=getattr(reel, "allow_comments", True),
                comments_count=18,
                merchant=MerchantFeedSummary(
                    id=merchant.id,
                    business_name=merchant.business_name,
                    sector=merchant_sector,
                    address=merchant.address_text,
                    distance_meters=distance_m
                ),
                coupon=coupon_summary
            )
            feed_items.append((distance_m, str(reel.id), item))

    feed_items.sort(key=lambda x: (x[0], x[1]))
    start_index = 0
    if cursor:
        try:
            decoded = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
            cursor_key = (float(decoded["distance"]), str(decoded["id"]))
            start_index = next(
                (index for index, item in enumerate(feed_items) if (item[0], item[1]) > cursor_key),
                len(feed_items),
            )
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid feed cursor.")

    page_items = feed_items[start_index:start_index + limit]
    sorted_reels = [item[2] for item in page_items]
    next_cursor = None
    if start_index + limit < len(feed_items) and page_items:
        last_distance, last_id, _ = page_items[-1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps({"distance": last_distance, "id": last_id}).encode("utf-8")
        ).decode("utf-8")

    return ResponseEnvelope(data=sorted_reels, meta={"next_cursor": next_cursor})


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please register your store profile before publishing showcase reels."
        )
    if merchant.kyc_status != "APPROVED" and getattr(merchant.kyc_status, "value", None) != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your merchant KYC must be approved before publishing reels."
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
        allow_comments=request.allow_comments,
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


@router.get("/reels/mine", response_model=ResponseEnvelope[List[ReelManagementOut]])
async def list_my_reels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found.")

    reels_res = await db.execute(
        select(Reel)
        .where(Reel.merchant_id == merchant.id)
        .order_by(Reel.created_at.desc())
    )
    return ResponseEnvelope(
        data=[
            ReelManagementOut(
                id=reel.id,
                title=reel.title,
                video_url=reel.video_url,
                thumbnail_url=reel.thumbnail_url,
                duration_seconds=reel.duration_seconds,
                status=reel.status.value if hasattr(reel.status, "value") else str(reel.status),
                rejection_reason=reel.rejection_reason,
                views_count=reel.views_count,
                allow_comments=reel.allow_comments,
                created_at=reel.created_at,
                updated_at=reel.updated_at,
                deleted_at=reel.deleted_at,
            )
            for reel in reels_res.scalars().all()
        ]
    )


@router.get("/reels/{reel_id}", response_model=ResponseEnvelope[ReelOut])
async def get_reel(reel_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Reel)
        .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        .where(
            Reel.id == reel_id,
            Reel.status == ReelStatus.APPROVED,
            Reel.deleted_at.is_(None),
        )
    )
    reel = result.scalars().first()
    if not reel or not reel.merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    merchant = reel.merchant
    sector = merchant.sector.value if hasattr(merchant.sector, "value") else str(merchant.sector)
    coupon = reel.coupon_template
    coupon_summary = None
    if coupon and coupon.is_active:
        coupon_summary = CouponFeedSummary(
            id=coupon.id,
            title=coupon.title,
            discount_type=coupon.discount_type.value if hasattr(coupon.discount_type, "value") else str(coupon.discount_type),
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
                sector=sector,
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
    db: AsyncSession = Depends(get_db)
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can update reels.")
    reel_res = await db.execute(
        select(Reel).where(Reel.id == reel_id, Reel.merchant_id == merchant.id)
    )
    reel = reel_res.scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    if reel.deleted_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Reel has been deactivated.")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(reel, field, value)
    await db.flush()
    await db.refresh(reel)
    return ResponseEnvelope(
        data=ReelManagementOut.model_validate(reel),
        message="Reel updated successfully.",
    )


@router.delete("/reels/{reel_id}", response_model=ResponseEnvelope[dict])
async def delete_reel(
    reel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can delete reels.")
    reel_res = await db.execute(
        select(Reel).where(Reel.id == reel_id, Reel.merchant_id == merchant.id)
    )
    reel = reel_res.scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")
    if not reel.deleted_at:
        reel.deleted_at = datetime.now(timezone.utc)
        await db.flush()
    return ResponseEnvelope(data={"reel_id": str(reel.id), "deleted": True}, message="Reel deactivated.")


@router.post("/reels/{reel_id}/view", response_model=ResponseEnvelope[dict])
async def record_reel_view(
    reel_id: uuid.UUID,
    viewer_key: Optional[str] = Query(None, max_length=128),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    reel_res = await db.execute(
        select(Reel).where(
            Reel.id == reel_id,
            Reel.status == ReelStatus.APPROVED,
            Reel.deleted_at.is_(None),
        )
    )
    reel = reel_res.scalars().first()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found.")

    today = datetime.now(timezone.utc).date()
    duplicate_query = select(ReelView).where(
        ReelView.reel_id == reel_id,
        ReelView.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
    )
    if current_user:
        duplicate_query = duplicate_query.where(ReelView.user_id == current_user.id)
    elif viewer_key:
        duplicate_query = duplicate_query.where(ReelView.viewer_key == viewer_key)
    else:
        duplicate_query = None

    if duplicate_query is not None:
        duplicate = (await db.execute(duplicate_query.limit(1))).scalars().first()
        if duplicate:
            return ResponseEnvelope(data={"reel_id": str(reel.id), "views_count": reel.views_count, "counted": False})

    db.add(ReelView(reel_id=reel.id, user_id=current_user.id if current_user else None, viewer_key=viewer_key))
    reel.views_count += 1
    await db.flush()
    return ResponseEnvelope(data={"reel_id": str(reel.id), "views_count": reel.views_count, "counted": True})
