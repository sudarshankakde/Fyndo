from typing import List
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.coupon import CouponStatus, CouponTemplate, UserCoupon
from app.models.notification import NotificationCategory
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.coupon import CouponClaimResponse, DynamicQrResponse, UserCouponWalletItem
from app.services.coupon_alerts import announce_coupon_enrolled
from app.services.notification_service import NotificationService
from app.services.reel_lifecycle_service import as_aware
from app.services.totp import TotpService

router = APIRouter()


def _role(role: object) -> str:
    return str(getattr(role, "value", role))


@router.get("/coupons/wallet", response_model=ResponseEnvelope[List[UserCouponWalletItem]])
async def get_user_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all coupons claimed by the authenticated shopper with real-time status."""
    stmt = (
        select(UserCoupon)
        .options(
            selectinload(UserCoupon.template).selectinload(CouponTemplate.merchant),
            selectinload(UserCoupon.template).selectinload(CouponTemplate.reel),
        )
        .where(UserCoupon.user_id == current_user.id)
        .order_by(UserCoupon.claimed_at.desc())
    )
    res = await db.execute(stmt)
    coupons = res.scalars().all()

    now = datetime.now(timezone.utc)
    wallet_items: List[UserCouponWalletItem] = []

    def is_expired_check(exp_dt: datetime) -> bool:
        if exp_dt.tzinfo is None:
            return exp_dt < datetime.now(timezone.utc).replace(tzinfo=None)
        return exp_dt < datetime.now(timezone.utc)

    for c in coupons:
        # Check expiry
        is_expired = is_expired_check(c.expires_at)
        c_status_str = c.status.value if hasattr(c.status, "value") else str(c.status)
        current_status = c_status_str
        if is_expired and c_status_str == "CLAIMED":
            c.status = CouponStatus.EXPIRED
            current_status = "EXPIRED"

        tmpl = c.template
        merch = tmpl.merchant if tmpl else None
        reel = tmpl.reel if tmpl else None
        d_type = tmpl.discount_type.value if tmpl and hasattr(tmpl.discount_type, "value") else (str(tmpl.discount_type) if tmpl else "PERCENTAGE")

        wallet_items.append(
            UserCouponWalletItem(
                id=c.id,
                coupon_template_id=c.coupon_template_id,
                title=tmpl.title if tmpl else "Discount Coupon",
                discount_type=d_type,
                discount_value=float(tmpl.discount_value) if tmpl else 0.0,
                min_order_amount=float(tmpl.min_order_amount) if tmpl else 0.0,
                validity_days=tmpl.validity_days if tmpl else 0,
                merchant_id=merch.id if merch else None,
                merchant_name=merch.business_name if merch else "Fyndo Partner",
                merchant_address=merch.address_text if merch else "",
                merchant_category=(merch.sector.value if hasattr(merch.sector, "value") else str(merch.sector)) if merch and merch.sector else None,
                merchant_logo_url=merch.logo_url if merch else None,
                merchant_cover_url=merch.cover_url if merch else None,
                merchant_profile_video_thumbnail_url=merch.profile_video_thumbnail_url if merch else None,
                reel_id=reel.id if reel else (tmpl.reel_id if tmpl else None),
                reel_thumbnail_url=reel.thumbnail_url if reel else None,
                reel_video_url=reel.video_url if reel else None,
                status=current_status,
                claimed_at=c.claimed_at,
                expires_at=c.expires_at,
                is_expired=is_expired
            )
        )

    await db.flush()
    return ResponseEnvelope(data=wallet_items)


@router.post("/coupons/{coupon_template_id}/claim", response_model=ResponseEnvelope[CouponClaimResponse])
async def claim_coupon(
    coupon_template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Claims a coupon template into the shopper's personal in-app wallet."""
    # Find template
    res = await db.execute(select(CouponTemplate).where(CouponTemplate.id == coupon_template_id))
    template = res.scalars().first()
    if not template or not template.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon offer not found or inactive.")
    offer_end = as_aware(template.expires_at)
    if offer_end is not None and offer_end <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This offer has ended.")

    # Check for active existing claim by this user
    existing_res = await db.execute(
        select(UserCoupon).where(
            and_(
                UserCoupon.coupon_template_id == coupon_template_id,
                UserCoupon.user_id == current_user.id,
                UserCoupon.status == CouponStatus.CLAIMED,
                UserCoupon.expires_at > datetime.now(timezone.utc)
            )
        )
    )
    if existing_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active claim for this coupon in your wallet."
        )

    # Compute expiration and secret
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=template.validity_days)
    totp_secret = TotpService.generate_secret()

    user_coupon = UserCoupon(
        coupon_template_id=template.id,
        user_id=current_user.id,
        status=CouponStatus.CLAIMED,
        totp_secret=totp_secret,
        claimed_at=now,
        expires_at=expires_at
    )
    db.add(user_coupon)
    await db.flush()
    await db.refresh(user_coupon)

    u_status = user_coupon.status.value if hasattr(user_coupon.status, "value") else str(user_coupon.status)
    audit_log(
        "coupon.claim",
        actor_id=current_user.id,
        actor_role=_role(current_user.role),
        target_type="user_coupon",
        target_id=user_coupon.id,
        coupon_template_id=template.id,
        merchant_id=template.merchant_id,
    )
    await NotificationService.notify_safe(
        db,
        user_id=current_user.id,
        event_type="coupon_claimed",
        title="Coupon added to wallet",
        body=f"\u201c{template.title}\u201d is ready. Show the QR at the store to redeem.",
        category=NotificationCategory.DEALS.value,
        action_type="COUPON",
        action_ref=str(user_coupon.id),
    )
    await announce_coupon_enrolled(db, template=template, user_coupon=user_coupon, shopper=current_user)
    return ResponseEnvelope(
        data=CouponClaimResponse(
            user_coupon_id=user_coupon.id,
            status=u_status,
            claimed_at=user_coupon.claimed_at,
            expires_at=user_coupon.expires_at
        ),
        message="Coupon claimed to wallet successfully!"
    )


@router.get("/coupons/{user_coupon_id}/dynamic-qr", response_model=ResponseEnvelope[DynamicQrResponse])
async def get_dynamic_qr(
    user_coupon_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates dynamic 60s rotating TOTP QR payload for in-store checkout.
    Tamper-proof against screenshots.
    """
    res = await db.execute(
        select(UserCoupon).where(
            and_(
                UserCoupon.id == user_coupon_id,
                UserCoupon.user_id == current_user.id
            )
        )
    )
    coupon = res.scalars().first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")

    c_status = coupon.status.value if hasattr(coupon.status, "value") else str(coupon.status)
    if c_status == "REDEEMED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon has already been redeemed.")

    exp = coupon.expires_at.replace(tzinfo=timezone.utc) if coupon.expires_at.tzinfo is None else coupon.expires_at
    if exp < datetime.now(timezone.utc):
        coupon.status = CouponStatus.EXPIRED
        await db.flush()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Coupon has expired.")

    payload, token, remaining, backup_pin = TotpService.generate_dynamic_qr_payload(
        user_coupon_id=coupon.id,
        secret=coupon.totp_secret,
        user_id=current_user.id
    )

    data = DynamicQrResponse(
        qr_payload=payload,
        totp_token=token,
        time_step_remaining_seconds=remaining,
        backup_offline_pin=backup_pin
    )
    return ResponseEnvelope(data=data)

