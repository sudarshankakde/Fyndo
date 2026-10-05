import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CouponClaimResponse(BaseModel):
    user_coupon_id: uuid.UUID
    status: str
    claimed_at: datetime
    expires_at: datetime


class DynamicQrResponse(BaseModel):
    qr_payload: str
    totp_token: str
    time_step_remaining_seconds: int
    backup_offline_pin: str


class RedemptionVerifyRequest(BaseModel):
    qr_payload: str
    cashier_lat: Optional[float] = None
    cashier_lon: Optional[float] = None


class RedemptionVerifyResponse(BaseModel):
    redemption_id: uuid.UUID
    status: str
    discount_applied: float
    customer_name: Optional[str] = None
    coupon_title: str
    timestamp: datetime


class UserCouponWalletItem(BaseModel):
    id: uuid.UUID
    coupon_template_id: uuid.UUID
    title: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    validity_days: int
    merchant_name: str
    merchant_address: str
    status: str
    claimed_at: datetime
    expires_at: datetime
    is_expired: bool

