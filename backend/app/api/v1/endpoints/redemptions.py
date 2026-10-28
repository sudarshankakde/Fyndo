import time
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional, Tuple
import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.v1.endpoints.auth import get_current_user, get_merchant_scope, MerchantScope
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import decode_access_token
from app.models.coupon import CouponStatus, CouponTemplate, DiscountType, RedemptionsLedger, UserCoupon
from app.models.merchant import KycStatus, Merchant, MerchantStaff
from app.models.reel import Reel
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.coupon import (
    MerchantRedemptionItem,
    PinRedemptionRequest,
    RedemptionHistoryItem,
    RedemptionPreviewRequest,
    RedemptionPreviewResponse,
    RedemptionVerifyRequest,
    RedemptionVerifyResponse,
)
from app.services.redemption_alerts import announce_redemption
from app.services.redemption_service import RedemptionService
from app.services.totp import TotpService
from app.utils.geo import calculate_haversine_distance

router = APIRouter()
security_bearer = HTTPBearer(auto_error=False)


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


@router.post("/redemptions/preview", response_model=ResponseEnvelope[RedemptionPreviewResponse])
async def preview_qr_coupon(
    request: RedemptionPreviewRequest,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    db: AsyncSession = Depends(get_db),
):
    """
    Cashier terminal scans customer's dynamic QR code.
    Pre-validates store ownership, expiration, and fresh TOTP before asking cashier for bill amount.
    """
    staff_merchant_id, _ = await get_staff_context(credentials)
    coupon, _ = await RedemptionService.validate_qr_for_staff(db, request.qr_payload, staff_merchant_id)

    discount_type = (
        coupon.template.discount_type.value
        if hasattr(coupon.template.discount_type, "value")
        else str(coupon.template.discount_type)
    )

    return ResponseEnvelope(
        data=RedemptionPreviewResponse(
            user_coupon_id=coupon.id,
            coupon_title=coupon.template.title,
            discount_type=discount_type,
            discount_value=float(coupon.template.discount_value),
            min_order_amount=float(coupon.template.min_order_amount),
            customer_name=coupon.user.full_name or coupon.user.phone,
            customer_phone=coupon.user.phone,
        ),
        message="Voucher verified successfully for this store.",
    )


@router.post("/redemptions/verify", response_model=ResponseEnvelope[RedemptionVerifyResponse])
async def verify_and_redeem(
    request: RedemptionVerifyRequest,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
    db: AsyncSession = Depends(get_db),
):
    """
    Cashier POS terminal scans customer's dynamic QR code.
    Verifies TOTP token, checks store geofence, and records redemption in the ledger.
    """
    staff_merchant_id, staff_id = await get_staff_context(credentials)
    coupon, totp_token = await RedemptionService.validate_qr_for_staff(db, request.qr_payload, staff_merchant_id)

    if request.bill_amount < float(coupon.template.min_order_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill amount must be at least ₹{float(coupon.template.min_order_amount):.2f}.",
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
            if settings.ENVIRONMENT.lower() != "development" and distance_offset > 500:  # Allow 500m radius tolerance
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
    discount_applied = RedemptionService.calculate_discount(
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
            customer_phone=coupon.user.phone if coupon.user else None,
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
    await RedemptionService.check_pin_rate_limit(staff_id, request.user_coupon_id)

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
    pin_valid = False
    if len(request.backup_pin) == 6 and request.backup_pin.isdigit():
        totp_calc = pyotp.TOTP(coupon.totp_secret, interval=60)
        for offset in (-1, 0, 1):
            if totp_calc.at(int(time.time()) + offset * 60) == request.backup_pin:
                pin_valid = True
                break
    else:
        pin_valid = TotpService.verify_backup_pin(coupon.totp_secret, request.backup_pin)

    if not pin_valid:
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
    discount = RedemptionService.calculate_discount(discount_type, float(coupon.template.discount_value), request.bill_amount)
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
            customer_phone=coupon.user.phone if coupon.user else None,
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
    scope: MerchantScope = Depends(get_merchant_scope),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RedemptionsLedger).where(RedemptionsLedger.merchant_id == scope.merchant_id)
    if scope.staff_id is not None:
        stmt = stmt.where(RedemptionsLedger.staff_id == scope.staff_id)
    if from_date:
        stmt = stmt.where(RedemptionsLedger.created_at >= from_date)
    if to_date:
        stmt = stmt.where(RedemptionsLedger.created_at <= to_date)
    redemptions = (await db.execute(stmt)).scalars().all()
    reels_count = (await db.execute(select(func.count(Reel.id)).where(Reel.merchant_id == scope.merchant_id, Reel.deleted_at.is_(None)))).scalar() or 0

    unique_cust_stmt = (
        select(func.count(func.distinct(UserCoupon.user_id)))
        .select_from(RedemptionsLedger)
        .join(UserCoupon, RedemptionsLedger.user_coupon_id == UserCoupon.id)
        .where(RedemptionsLedger.merchant_id == scope.merchant_id)
    )
    if scope.staff_id is not None:
        unique_cust_stmt = unique_cust_stmt.where(RedemptionsLedger.staff_id == scope.staff_id)
    if from_date:
        unique_cust_stmt = unique_cust_stmt.where(RedemptionsLedger.created_at >= from_date)
    if to_date:
        unique_cust_stmt = unique_cust_stmt.where(RedemptionsLedger.created_at <= to_date)
    unique_customers = (await db.execute(unique_cust_stmt)).scalar() or 0

    return ResponseEnvelope(data={
        "merchant_id": str(scope.merchant_id),
        "redemption_count": len(redemptions),
        "total_bill_amount": round(sum(float(item.bill_amount) for item in redemptions), 2),
        "total_discount_applied": round(sum(float(item.discount_applied) for item in redemptions), 2),
        "unique_customers": int(unique_customers),
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
            merchant_is_verified=bool(merchant.kyc_status == KycStatus.APPROVED),
            staff_name=staff.staff_name if staff else None,
            discount_type=template.discount_type.value if hasattr(template.discount_type, "value") else str(template.discount_type),
            bill_amount=float(ledger.bill_amount),
            discount_applied=float(ledger.discount_applied),
            created_at=ledger.created_at,
        )
        for ledger, coupon, template, merchant, staff in rows
    ])
