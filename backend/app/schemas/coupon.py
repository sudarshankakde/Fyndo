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
    bill_amount: float = Field(..., gt=0)
    cashier_lat: Optional[float] = None
    cashier_lon: Optional[float] = None


class RedemptionVerifyResponse(BaseModel):
    redemption_id: uuid.UUID
    status: str
    discount_applied: float
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    coupon_title: str
    timestamp: datetime
    bill_amount: float


class PinRedemptionRequest(BaseModel):
    user_coupon_id: uuid.UUID
    backup_pin: str = Field(..., min_length=4, max_length=6)
    bill_amount: float = Field(..., gt=0)
    cashier_lat: Optional[float] = None
    cashier_lon: Optional[float] = None


class RedemptionHistoryItem(BaseModel):
    redemption_id: uuid.UUID
    coupon_id: uuid.UUID
    coupon_title: str
    merchant_id: uuid.UUID
    merchant_name: str
    merchant_is_verified: bool = False
    staff_name: Optional[str] = None
    discount_type: str
    bill_amount: float
    discount_applied: float
    created_at: datetime

    model_config = {"from_attributes": True}


class MerchantRedemptionItem(BaseModel):
    redemption_id: uuid.UUID
    coupon_id: uuid.UUID
    coupon_title: str
    shopper_name: Optional[str] = None
    bill_amount: float
    discount_applied: float
    staff_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCouponWalletItem(BaseModel):
    id: uuid.UUID
    coupon_template_id: uuid.UUID
    title: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    validity_days: int
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: str
    merchant_is_verified: bool = False
    merchant_address: str
    merchant_category: Optional[str] = None
    merchant_logo_url: Optional[str] = None
    merchant_cover_url: Optional[str] = None
    merchant_profile_video_thumbnail_url: Optional[str] = None
    reel_id: Optional[uuid.UUID] = None
    reel_thumbnail_url: Optional[str] = None
    reel_video_url: Optional[str] = None
    status: str
    claimed_at: datetime
    expires_at: datetime
    is_expired: bool
    terms: Optional[str] = None

    model_config = {"from_attributes": True}


class RedemptionPreviewRequest(BaseModel):
    qr_payload: str


class RedemptionPreviewResponse(BaseModel):
    user_coupon_id: uuid.UUID
    coupon_title: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
