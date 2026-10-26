"""Storefront engagement: profile video, call taps, follows, ratings, cashier access.

Registered ahead of ``merchants.router`` so literal paths such as
``/merchants/following`` win over ``/merchants/{merchant_id}``.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, get_optional_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.merchant import KycStatus, Merchant, MerchantStaff
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.merchant import StaffOut
from app.schemas.merchant_engagement import (
    CallTrackRequest,
    CallTrackResponse,
    FollowedMerchantOut,
    FollowToggleResponse,
    MerchantInsightsOut,
    ProfileVideoOut,
    ProfileVideoUpdateRequest,
    RatingCreateRequest,
    RatingOut,
    RatingSummaryOut,
    StaffPermissionUpdateRequest,
)
from app.services import merchant_engagement_service as engagement

router = APIRouter()


def _val(value) -> str:
    return str(getattr(value, "value", value))


async def _owned_merchant(db: AsyncSession, user: User) -> Merchant:
    merchant = (
        await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    ).scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only store owners can do this.")
    return merchant


async def _public_merchant(db: AsyncSession, merchant_id: uuid.UUID) -> Merchant:
    merchant = (
        await db.execute(
            select(Merchant).where(Merchant.id == merchant_id, Merchant.kyc_status == KycStatus.APPROVED)
        )
    ).scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found.")
    return merchant


@router.patch("/merchants/me/profile-video", response_model=ResponseEnvelope[ProfileVideoOut])
async def update_profile_video(
    request: ProfileVideoUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sets the store's permanent showcase video (never expires, unlike reels)."""
    merchant = await _owned_merchant(db, current_user)
    merchant.profile_video_url = request.profile_video_url
    merchant.profile_video_thumbnail_url = request.profile_video_thumbnail_url
    await db.flush()
    return ResponseEnvelope(
        data=ProfileVideoOut(
            merchant_id=merchant.id,
            profile_video_url=merchant.profile_video_url,
            profile_video_thumbnail_url=merchant.profile_video_thumbnail_url,
        ),
        message="Store video updated.",
    )


@router.get("/merchants/me/insights", response_model=ResponseEnvelope[MerchantInsightsOut])
async def get_merchant_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant = await _owned_merchant(db, current_user)
    return ResponseEnvelope(data=MerchantInsightsOut(**await engagement.merchant_insights(db, merchant)))


@router.get("/merchants/following", response_model=ResponseEnvelope[List[FollowedMerchantOut]])
async def list_followed_merchants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await engagement.list_following(db, current_user)
    return ResponseEnvelope(
        data=[
            FollowedMerchantOut(
                id=merchant.id,
                business_name=merchant.business_name,
                sector=_val(merchant.sector),
                city=merchant.city,
                address_text=merchant.address_text,
                profile_video_thumbnail_url=merchant.profile_video_thumbnail_url,
                logo_url=merchant.logo_url,
                cover_url=merchant.cover_url,
                followed_at=followed_at,
            )
            for merchant, followed_at in rows
        ]
    )


@router.patch("/merchants/staff/{staff_id}/permissions", response_model=ResponseEnvelope[StaffOut])
async def update_staff_permissions(
    staff_id: uuid.UUID,
    request: StaffPermissionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner grants or revokes the cashier's ability to upload reels."""
    merchant = await _owned_merchant(db, current_user)
    staff = (
        await db.execute(
            select(MerchantStaff).where(
                MerchantStaff.id == staff_id, MerchantStaff.merchant_id == merchant.id
            )
        )
    ).scalars().first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")
    staff.can_upload_reels = request.can_upload_reels
    await db.flush()
    await db.refresh(staff)
    audit_log(
        "merchant_staff.permissions",
        actor_id=current_user.id,
        actor_role=_val(current_user.role),
        target_type="merchant_staff",
        target_id=staff.id,
        can_upload_reels=staff.can_upload_reels,
    )
    message = "Staff can now upload reels." if staff.can_upload_reels else "Staff can no longer upload reels."
    return ResponseEnvelope(data=StaffOut.model_validate(staff), message=message)


@router.post("/merchants/{merchant_id}/track-call", response_model=ResponseEnvelope[CallTrackResponse])
async def track_call_click(
    merchant_id: uuid.UUID,
    request: CallTrackRequest | None = None,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    await _public_merchant(db, merchant_id)
    fingerprint = request.device_fingerprint if request else None
    counted = await engagement.track_call(db, merchant_id, current_user, fingerprint)
    return ResponseEnvelope(data=CallTrackResponse(counted=counted))


@router.post("/merchants/{merchant_id}/follow", response_model=ResponseEnvelope[FollowToggleResponse])
async def toggle_follow_merchant(
    merchant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant = await _public_merchant(db, merchant_id)
    if merchant.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot follow your own store.")
    following, count = await engagement.toggle_follow(db, merchant_id, current_user)
    return ResponseEnvelope(
        data=FollowToggleResponse(merchant_id=merchant_id, is_following=following, followers_count=count),
        message="Following this store." if following else "Unfollowed this store.",
    )


@router.post("/merchants/{merchant_id}/rate", response_model=ResponseEnvelope[RatingOut])
async def rate_merchant(
    merchant_id: uuid.UUID,
    request: RatingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant = await _public_merchant(db, merchant_id)
    if merchant.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot rate your own store.")
    review = (request.review_text or "").strip() or None
    row = await engagement.upsert_rating(db, merchant_id, current_user, request.rating, review)
    return ResponseEnvelope(
        data=RatingOut(
            id=row.id,
            rating=row.rating,
            review_text=row.review_text,
            user_name=current_user.full_name or "Fyndo shopper",
            updated_at=row.updated_at,
        ),
        message="Thanks for rating this store!",
    )


@router.get("/merchants/{merchant_id}/ratings", response_model=ResponseEnvelope[RatingSummaryOut])
async def get_merchant_ratings(
    merchant_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    await _public_merchant(db, merchant_id)
    summary = await engagement.rating_summary(db, merchant_id)
    reviews = await engagement.recent_reviews(db, merchant_id, limit)
    my_rating = await engagement.user_rating(db, merchant_id, current_user)
    return ResponseEnvelope(
        data=RatingSummaryOut(
            merchant_id=merchant_id,
            my_rating=my_rating,
            reviews=[
                RatingOut(
                    id=r.id,
                    rating=r.rating,
                    review_text=r.review_text,
                    user_name=user.full_name or "Fyndo shopper",
                    updated_at=r.updated_at,
                )
                for r, user in reviews
            ],
            **summary,
        )
    )
