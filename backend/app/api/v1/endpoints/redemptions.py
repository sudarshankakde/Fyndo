import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import decode_access_token
from app.models.coupon import CouponStatus, CouponTemplate, DiscountType, RedemptionsLedger, UserCoupon
from app.models.merchant import Merchant, MerchantStaff
from app.models.reel import Reel
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.coupon import (
    MerchantRedemptionItem,
    PinRedemptionRequest,
    RedemptionHistoryItem,
    RedemptionVerifyRequest,
    RedemptionVerifyResponse,
)
from app.services.redemption_alerts import announce_redemption
from app.services.totp import TotpService
from app.utils.geo import calculate_haversine_distance

router = APIRouter()
security_bearer = HTTPBearer(auto_error=False)


def calculate_discount(discount_type: str, discount_value: float, bill_amount: float) -> float:
    if discount_type == DiscountType.PERCENTAGE.value:
        return round(min(bill_amount, bill_amount * discount_value / 100), 2)
    if discount_type == DiscountType.FLAT_AMOUNT.value:
        return round(min(bill_amount, discount_value), 2)
    return round(min(bill_amount, discount_value), 2)


async def get_staff_context(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Tuple[uuid.UUID, uuid.UUID]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff POS authentication required.")
    token_data = decode_access_token(credentials.credentials)
    if not token_data or token_data.get("role") != "ROLE_CASHIER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only authorized merchant staff can redeem.")
    try:
        return uuid.UUID(token_data["merchant_id"]), uuid.UUID(token_data["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid staff authentication claims.")


async def check_pin_rate_limit(staff_id: uuid.UUID, coupon_id: uuid.UUID) -> None:
    redis = await get_redis_client()
    key = f"rate:backup-pin:{staff_id}:{coupon_id}"
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, 600)
    if attempts > 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many backup PIN attempts.")


@router.post("/redemptions/verify", response_model=ResponseEnvelope[RedemptionVerifyResponse])
async def verify_and_redeem(
    request: RedemptionVerifyRequest,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    db: AsyncSession = Depends(get_db)
):
    """
    Cashier POS terminal scans customer's dynamic QR code.
    Verifies TOTP token, checks store geofence, and records redemption in the ledger.
    """
    staff_merchant_id, staff_id = await get_staff_context(credentials)

    # Decode and parse QR payload
    parsed = TotpService.parse_qr_payload(request.qr_payload)
    if not parsed or "claim_id" not in parsed or "totp" not in parsed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed or unreadable QR payload.")

    claim_id = uuid.UUID(parsed["claim_id"])
    totp_token = parsed["totp"]

    # Fetch claimed coupon
    stmt = (
        select(UserCoupon)
        .options(selectinload(UserCoupon.template), selectinload(UserCoupon.user))
        .where(UserCoupon.id == claim_id)
    )
    res = await db.execute(stmt)
    coupon = res.scalars().first()

    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon claim record not found.")

    c_status = coupon.status.value if hasattr(coupon.status, "value") else str(coupon.status)
    if c_status == "REDEEMED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Voucher already redeemed at {coupon.redeemed_at.strftime('%H:%M') if coupon.redeemed_at else 'earlier'}."
        )

    exp = coupon.expires_at.replace(tzinfo=timezone.utc) if coupon.expires_at.tzinfo is None else coupon.expires_at
    if exp < datetime.now(timezone.utc):
        coupon.status = CouponStatus.EXPIRED
        await db.flush()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This coupon has expired.")

    # Check merchant ownership
    if coupon.template.merchant_id != staff_merchant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This coupon belongs to a different merchant."
        )

    if request.bill_amount < float(coupon.template.min_order_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill amount must be at least {float(coupon.template.min_order_amount):.2f}.",
        )

    # Verify dynamic TOTP cryptographic token
    is_valid_totp = TotpService.verify_token(coupon.totp_secret, totp_token)
    if not is_valid_totp:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="QR code expired. Please ask customer to refresh their screen."
        )

    # Optional: Verify Geofence if coordinates are provided
    distance_offset = None
    if request.cashier_lat is not None and request.cashier_lon is not None:
        merch_res = await db.execute(select(Merchant).where(Merchant.id == staff_merchant_id))
        merchant = merch_res.scalars().first()
        if merchant:
            distance_offset = calculate_haversine_distance(
                request.cashier_lat, request.cashier_lon, merchant.latitude, merchant.longitude
            )
            if distance_offset > 500:  # Allow 500m radius tolerance
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cashier location exceeds allowed store perimeter ({distance_offset}m away)."
                )

    # Commit redemption through an atomic single-winner guard: the UPDATE only
    # succeeds while the claim is still CLAIMED, so two cashiers scanning the
    # same voucher concurrently cannot double-spend it.
    now = datetime.now(timezone.utc)
    claim_result = await db.execute(
        update(UserCoupon)
        .where(UserCoupon.id == coupon.id, UserCoupon.status == CouponStatus.CLAIMED)
        .values(
            status=CouponStatus.REDEEMED,
            redeemed_at=now,
            redeemed_by_staff_id=staff_id,
        )
        .execution_options(synchronize_session=False)
    )
    if claim_result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This coupon has already been redeemed.",
        )

    discount_type = coupon.template.discount_type.value if hasattr(coupon.template.discount_type, "value") else str(coupon.template.discount_type)
    discount_applied = calculate_discount(
        discount_type,
        float(coupon.template.discount_value),
        request.bill_amount,
    )
    ledger_entry = RedemptionsLedger(
        user_coupon_id=coupon.id,
        merchant_id=staff_merchant_id,
        staff_id=staff_id,
        bill_amount=request.bill_amount,
        discount_applied=discount_applied,
        cashier_latitude=request.cashier_lat,
        cashier_longitude=request.cashier_lon,
        distance_from_shop_m=distance_offset,
        created_at=now
    )
    db.add(ledger_entry)
    await db.flush()

    customer_name = coupon.user.full_name or coupon.user.phone
    await announce_redemption(
        db, coupon=coupon, ledger=ledger_entry, merchant_id=staff_merchant_id, method="QR"
    )

    return ResponseEnvelope(
        data=RedemptionVerifyResponse(
            redemption_id=ledger_entry.id,
            status="VERIFIED_AND_REDEEMED",
            discount_applied=float(ledger_entry.discount_applied),
            customer_name=customer_name,
            coupon_title=coupon.template.title,
            timestamp=now,
            bill_amount=request.bill_amount,
        ),
        message="Coupon successfully verified and redeemed!"
    )


@router.post("/redemptions/verify-pin", response_model=ResponseEnvelope[RedemptionVerifyResponse])
async def verify_backup_pin(
    request: PinRedemptionRequest,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    db: AsyncSession = Depends(get_db),
):
    staff_merchant_id, staff_id = await get_staff_context(credentials)
    await check_pin_rate_limit(staff_id, request.user_coupon_id)

    result = await db.execute(
        select(UserCoupon)
        .options(selectinload(UserCoupon.template), selectinload(UserCoupon.user))
        .where(UserCoupon.id == request.user_coupon_id)
    )
    coupon = result.scalars().first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon claim record not found.")
    if coupon.template.merchant_id != staff_merchant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This coupon belongs to a different merchant.")
    if coupon.status != CouponStatus.CLAIMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon is no longer redeemable.")
    if coupon.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        coupon.status = CouponStatus.EXPIRED
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This coupon has expired.")
    if coupon.backup_pin_used_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Backup PIN has already been used.")
    if request.bill_amount < float(coupon.template.min_order_amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill amount is below the coupon minimum.")
    if not TotpService.verify_backup_pin(coupon.totp_secret, request.backup_pin):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired backup PIN.")

    # Atomic single-winner guard (see /redemptions/verify) — the backup PIN may
    # only ever be consumed once, even under concurrent terminal requests.
    now = datetime.now(timezone.utc)
    claim_result = await db.execute(
        update(UserCoupon)
        .where(UserCoupon.id == coupon.id, UserCoupon.status == CouponStatus.CLAIMED)
        .values(
            status=CouponStatus.REDEEMED,
            redeemed_at=now,
            backup_pin_used_at=now,
            redeemed_by_staff_id=staff_id,
        )
        .execution_options(synchronize_session=False)
    )
    if claim_result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This coupon has already been redeemed.",
        )

    discount_type = coupon.template.discount_type.value if hasattr(coupon.template.discount_type, "value") else str(coupon.template.discount_type)
    discount = calculate_discount(discount_type, float(coupon.template.discount_value), request.bill_amount)
    ledger = RedemptionsLedger(
        user_coupon_id=coupon.id,
        merchant_id=staff_merchant_id,
        staff_id=staff_id,
        bill_amount=request.bill_amount,
        discount_applied=discount,
        cashier_latitude=request.cashier_lat,
        cashier_longitude=request.cashier_lon,
        created_at=now,
    )
    db.add(ledger)
    await db.flush()
    await announce_redemption(
        db, coupon=coupon, ledger=ledger, merchant_id=staff_merchant_id, method="BACKUP_PIN"
    )
    return ResponseEnvelope(
        data=RedemptionVerifyResponse(
            redemption_id=ledger.id,
            status="VERIFIED_AND_REDEEMED",
            discount_applied=discount,
            customer_name=coupon.user.full_name or coupon.user.phone,
            coupon_title=coupon.template.title,
            timestamp=now,
            bill_amount=request.bill_amount,
        ),
        message="Coupon successfully verified and redeemed with backup PIN.",
    )


@router.get("/merchants/redemptions", response_model=ResponseEnvelope[list[MerchantRedemptionItem]])
async def merchant_redemption_history(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can view redemptions.")

    stmt = (
        select(RedemptionsLedger, UserCoupon, CouponTemplate, User)
        .join(UserCoupon, RedemptionsLedger.user_coupon_id == UserCoupon.id)
        .join(CouponTemplate, UserCoupon.coupon_template_id == CouponTemplate.id)
        .join(User, UserCoupon.user_id == User.id)
        .where(RedemptionsLedger.merchant_id == merchant.id)
        .order_by(RedemptionsLedger.created_at.desc())
    )
    if from_date:
        stmt = stmt.where(RedemptionsLedger.created_at >= from_date)
    if to_date:
        stmt = stmt.where(RedemptionsLedger.created_at <= to_date)
    rows = (await db.execute(stmt)).all()
    return ResponseEnvelope(data=[
        MerchantRedemptionItem(
            redemption_id=ledger.id,
            coupon_id=coupon.id,
            coupon_title=template.title,
            shopper_name=user.full_name or user.phone,
            bill_amount=float(ledger.bill_amount),
            discount_applied=float(ledger.discount_applied),
            staff_id=ledger.staff_id,
            created_at=ledger.created_at,
        )
        for ledger, coupon, template, user in rows
    ])


@router.get("/merchants/analytics", response_model=ResponseEnvelope[dict])
async def merchant_analytics(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can view analytics.")

    stmt = select(RedemptionsLedger).where(RedemptionsLedger.merchant_id == merchant.id)
    if from_date:
        stmt = stmt.where(RedemptionsLedger.created_at >= from_date)
    if to_date:
        stmt = stmt.where(RedemptionsLedger.created_at <= to_date)
    redemptions = (await db.execute(stmt)).scalars().all()
    reels_count = (await db.execute(select(func.count(Reel.id)).where(Reel.merchant_id == merchant.id, Reel.deleted_at.is_(None)))).scalar() or 0
    return ResponseEnvelope(data={
        "merchant_id": str(merchant.id),
        "redemption_count": len(redemptions),
        "total_bill_amount": round(sum(float(item.bill_amount) for item in redemptions), 2),
        "total_discount_applied": round(sum(float(item.discount_applied) for item in redemptions), 2),
        "reels_count": reels_count,
        "from_date": from_date,
        "to_date": to_date,
    })


@router.get("/redemptions/my-history", response_model=ResponseEnvelope[list[RedemptionHistoryItem]])
async def shopper_redemption_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(RedemptionsLedger, UserCoupon, CouponTemplate, Merchant, MerchantStaff)
        .join(UserCoupon, RedemptionsLedger.user_coupon_id == UserCoupon.id)
        .join(CouponTemplate, UserCoupon.coupon_template_id == CouponTemplate.id)
        .join(Merchant, RedemptionsLedger.merchant_id == Merchant.id)
        .outerjoin(MerchantStaff, RedemptionsLedger.staff_id == MerchantStaff.id)
        .where(UserCoupon.user_id == current_user.id)
        .order_by(RedemptionsLedger.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return ResponseEnvelope(data=[
        RedemptionHistoryItem(
            redemption_id=ledger.id,
            coupon_id=coupon.id,
            coupon_title=template.title,
            merchant_id=merchant.id,
            merchant_name=merchant.business_name,
            staff_name=staff.staff_name if staff else None,
            discount_type=template.discount_type.value if hasattr(template.discount_type, "value") else str(template.discount_type),
            bill_amount=float(ledger.bill_amount),
            discount_applied=float(ledger.discount_applied),
            created_at=ledger.created_at,
        )
        for ledger, coupon, template, merchant, staff in rows
    ])
