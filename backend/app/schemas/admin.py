import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ModerationDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE or REJECT")
    rejection_reason: Optional[str] = None


class MerchantKycDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE or REJECT")
    rejection_reason: Optional[str] = Field(None, max_length=500)


class AdminReelListItem(BaseModel):
    id: uuid.UUID
    title: str
    video_url: str
    thumbnail_url: str
    duration_seconds: int
    audio_type: str
    status: str
    merchant_id: uuid.UUID
    merchant_name: str
    sector: str
    city: str
    coupon_title: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_order_amount: Optional[float] = None
    validity_days: Optional[int] = None


class AdminStatsResponse(BaseModel):
    total_merchants: int
    total_users: int
    total_reels: int
    total_redemptions: int
    total_discount_applied: float
    pending_moderation_count: int


class AdminMerchantDetail(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    address_text: str
    city: str
    latitude: float
    longitude: float
    owner_phone: str
    kyc_status: str
    staff_name: Optional[str] = None
    staff_phone: Optional[str] = None
    reels_count: int = 0
    created_at: datetime


class AdminMerchantCreateRequest(BaseModel):
    owner_phone: str = Field(..., description="Registered owner phone +91XXXXXXXXXX")
    business_name: str = Field(..., min_length=2, max_length=150)
    sector: str = Field("FOOD", description="FOOD, FASHION, FOOTWEAR, ELECTRONICS, REAL_ESTATE")
    address_text: str = Field(..., min_length=5)
    city: str = Field("Nagpur", description="Nagpur or Mumbai")
    latitude: float = Field(21.1458)
    longitude: float = Field(79.0882)
    gstin: Optional[str] = None
    staff_name: Optional[str] = "Store Cashier"
    staff_pin: Optional[str] = "123456"


class AdminMerchantUpdateRequest(BaseModel):
    business_name: Optional[str] = None
    sector: Optional[str] = None
    address_text: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gstin: Optional[str] = None
    kyc_status: Optional[str] = None


class AdminReelCreateRequest(BaseModel):
    merchant_id: uuid.UUID
    title: str = Field(..., min_length=2, max_length=150)
    video_url: str = Field(..., min_length=10)
    thumbnail_url: str = Field(..., min_length=10)
    duration_seconds: int = Field(30, ge=15, le=60)
    coupon_title: str = Field(..., min_length=2, max_length=100)
    discount_type: str = Field("PERCENTAGE", description="PERCENTAGE, FLAT_AMOUNT, BOGO")
    discount_value: float = Field(..., gt=0)
    validity_days: int = Field(5, ge=1, le=60)
    min_order_amount: float = Field(0.0, ge=0)


class AdminReelUpdateRequest(BaseModel):
    title: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[str] = None
    coupon_title: Optional[str] = None
    discount_value: Optional[float] = None
    validity_days: Optional[int] = None


class AdminStaffUpdateRequest(BaseModel):
    staff_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., description="+91XXXXXXXXXX")
    pin: str = Field(..., min_length=6, max_length=6)


class SystemSettingOut(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    updated_at: Optional[datetime] = None


class SystemSettingsUpdateRequest(BaseModel):
    auto_approve_reels: Optional[bool] = None
