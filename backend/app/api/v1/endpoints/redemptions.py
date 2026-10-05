import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.coupon import CouponStatus, RedemptionsLedger, UserCoupon
from app.models.merchant import Merchant
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.coupon import RedemptionVerifyRequest, RedemptionVerifyResponse
from app.services.totp import TotpService
from app.utils.geo import calculate_haversine_distance

router = APIRouter()
security_bearer = HTTPBearer(auto_error=False)


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
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff POS authentication required.")

    token_data = decode_access_token(credentials.credentials)
    if not token_data or "merchant_id" not in token_data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only authorized merchant staff can redeem.")

    staff_merchant_id = uuid.UUID(token_data["merchant_id"])
    staff_id = uuid.UUID(token_data["sub"])

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

    # Commit redemption
    now = datetime.now(timezone.utc)
    coupon.status = CouponStatus.REDEEMED
    coupon.redeemed_at = now
    coupon.redeemed_by_staff_id = staff_id

    ledger_entry = RedemptionsLedger(
        user_coupon_id=coupon.id,
        merchant_id=staff_merchant_id,
        staff_id=staff_id,
        discount_applied=float(coupon.template.discount_value),
        cashier_latitude=request.cashier_lat,
        cashier_longitude=request.cashier_lon,
        distance_from_shop_m=distance_offset,
        created_at=now
    )
    db.add(ledger_entry)
    await db.flush()

    customer_name = coupon.user.full_name or coupon.user.phone

    return ResponseEnvelope(
        data=RedemptionVerifyResponse(
            redemption_id=ledger_entry.id,
            status="VERIFIED_AND_REDEEMED",
            discount_applied=float(ledger_entry.discount_applied),
            customer_name=customer_name,
            coupon_title=coupon.template.title,
            timestamp=now
        ),
        message="Coupon successfully verified and redeemed!"
    )
