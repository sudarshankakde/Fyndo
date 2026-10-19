"""Proximity feed construction for the reels discovery screen.

Performance notes
-----------------
The original implementation loaded *every* approved reel into memory and
sorted it in Python. This version:

  * narrows the candidate set in the database with a latitude/longitude
    bounding box (index-friendly) before the precise Haversine refinement,
  * caps the candidate set with `MAX_FEED_CANDIDATES`,
  * fetches like/comment aggregates only for the page being returned,
  * caches serialized pages in Redis for a short TTL.
"""
import base64
import json
import logging
import math
import uuid
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis_client
from app.models.coupon import CouponTemplate
from app.models.merchant import Merchant
from app.models.reel import Reel, ReelStatus
from app.models.reel_engagement import ReelComment, ReelLike
from app.models.user import User
from app.schemas.reel import CouponFeedSummary, MerchantFeedSummary, ReelOut
from app.services.reel_lifecycle_service import live_offer_clause
from app.utils.geo import calculate_haversine_distance

logger = logging.getLogger("fyndo.reel_feed")

KM_PER_DEGREE_LAT = 111.045
MAX_FEED_CANDIDATES = 500
FEED_CACHE_TTL_SECONDS = 30


def _cache_key(lat, lon, radius_km, sector, limit, cursor, user) -> str:
    identity = str(user.id) if user else "anon"
    return (
        f"feed:{round(lat, 3)}:{round(lon, 3)}:{radius_km}:"
        f"{(sector or 'ALL').upper()}:{limit}:{cursor or 'START'}:{identity}"
    )


async def _cache_get(key: str) -> Optional[dict]:
    try:
        redis = await get_redis_client()
        raw = await redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug(f"Feed cache read skipped: {exc}")
        return None


async def _cache_set(key: str, payload: dict) -> None:
    try:
        redis = await get_redis_client()
        await redis.set(key, json.dumps(payload), ex=FEED_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.debug(f"Feed cache write skipped: {exc}")


def _encode_cursor(distance_m: int, reel_id: str) -> str:
    raw = json.dumps({"distance": distance_m, "id": reel_id}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_cursor(cursor: str) -> Tuple[float, str]:
    decoded = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    return float(decoded["distance"]), str(decoded["id"])


async def _count_map(db: AsyncSession, model, reel_ids: List[uuid.UUID]) -> Dict[uuid.UUID, int]:
    if not reel_ids:
        return {}
    rows = (
        await db.execute(
            select(model.reel_id, func.count(model.id))
            .where(model.reel_id.in_(reel_ids))
            .group_by(model.reel_id)
        )
    ).all()
    return {reel_id: count for reel_id, count in rows}


def _coupon_summary(reel: Reel) -> Optional[CouponFeedSummary]:
    template: Optional[CouponTemplate] = reel.coupon_template
    if not template or not template.is_active:
        return None
    d_type = getattr(template.discount_type, "value", str(template.discount_type))
    return CouponFeedSummary(
        id=template.id,
        title=template.title,
        discount_type=d_type,
        discount_value=float(template.discount_value),
        min_order_amount=float(template.min_order_amount),
        validity_days=template.validity_days,
        expires_at=template.expires_at,
    )


async def _query_feed(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_km: int,
    sector: Optional[str],
    limit: int,
    cursor: Optional[str],
    current_user: Optional[User],
) -> Tuple[List[ReelOut], Optional[str]]:
    lat_delta = radius_km / KM_PER_DEGREE_LAT
    lon_scale = max(math.cos(math.radians(lat)), 0.01)
    lon_delta = radius_km / (KM_PER_DEGREE_LAT * lon_scale)

    stmt = (
        select(Reel)
        .join(Merchant, Reel.merchant_id == Merchant.id)
        .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
        .where(Reel.status == ReelStatus.APPROVED)
        .where(Reel.deleted_at.is_(None))
        .where(live_offer_clause())
        .where(Merchant.latitude.between(lat - lat_delta, lat + lat_delta))
        .where(Merchant.longitude.between(lon - lon_delta, lon + lon_delta))
        .order_by(Reel.created_at.desc())
        .limit(MAX_FEED_CANDIDATES)
    )
    if sector:
        stmt = stmt.where(Merchant.sector == sector.strip().upper())

    reels = (await db.execute(stmt)).scalars().all()

    radius_meters = radius_km * 1000
    scored: List[Tuple[int, str, Reel, Merchant]] = []
    for reel in reels:
        merchant = reel.merchant
        if not merchant:
            continue
        distance_m = calculate_haversine_distance(
            lat, lon, merchant.latitude, merchant.longitude
        )
        if distance_m <= radius_meters:
            scored.append((distance_m, str(reel.id), reel, merchant))

    scored.sort(key=lambda row: (row[0], row[1]))

    start_index = 0
    if cursor:
        cursor_key = _decode_cursor(cursor)
        start_index = next(
            (index for index, row in enumerate(scored) if (row[0], row[1]) > cursor_key),
            len(scored),
        )

    page = scored[start_index:start_index + limit]
    reel_ids = [row[2].id for row in page]
    like_counts = await _count_map(db, ReelLike, reel_ids)
    comment_counts = await _count_map(db, ReelComment, reel_ids)

    liked_ids: set = set()
    if current_user and reel_ids:
        liked_ids = set(
            (
                await db.execute(
                    select(ReelLike.reel_id).where(
                        ReelLike.user_id == current_user.id,
                        ReelLike.reel_id.in_(reel_ids),
                    )
                )
            ).scalars().all()
        )

    items: List[ReelOut] = []
    for distance_m, _, reel, merchant in page:
        merchant_sector = getattr(merchant.sector, "value", str(merchant.sector))
        items.append(
            ReelOut(
                id=reel.id,
                title=reel.title,
                video_url=reel.video_url,
                thumbnail_url=reel.thumbnail_url,
                duration_seconds=reel.duration_seconds,
                views_count=reel.views_count,
                likes_count=int(like_counts.get(reel.id, 0)),
                is_liked=reel.id in liked_ids,
                allow_comments=bool(getattr(reel, "allow_comments", True)),
                comments_count=int(comment_counts.get(reel.id, 0)),
                merchant=MerchantFeedSummary(
                    id=merchant.id,
                    business_name=merchant.business_name,
                    sector=merchant_sector,
                    address=merchant.address_text,
                    distance_meters=distance_m,
                ),
                coupon=_coupon_summary(reel),
            )
        )

    next_cursor = None
    if page and start_index + limit < len(scored):
        last_distance, last_id, _, _ = page[-1]
        next_cursor = _encode_cursor(last_distance, last_id)

    return items, next_cursor


async def build_feed(
    db: AsyncSession,
    *,
    lat: float,
    lon: float,
    radius_km: int,
    sector: Optional[str],
    limit: int,
    cursor: Optional[str],
    current_user: Optional[User],
) -> Tuple[List[ReelOut], Optional[str]]:
    """Returns a page of proximity-ordered reels plus the next cursor."""
    cache_key = _cache_key(lat, lon, radius_km, sector, limit, cursor, current_user)
    cached = await _cache_get(cache_key)
    if cached is not None:
        return [ReelOut.model_validate(entry) for entry in cached.get("items", [])], cached.get("next_cursor")

    items, next_cursor = await _query_feed(
        db, lat, lon, radius_km, sector, limit, cursor, current_user
    )
    await _cache_set(
        cache_key,
        {"items": [item.model_dump(mode="json") for item in items], "next_cursor": next_cursor},
    )
    return items, next_cursor
