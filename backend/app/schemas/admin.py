import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.merchant import SubscriptionStatus


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
    gstin: Optional[str] = None
    shop_act: Optional[str] = None
    udyam: Optional[str] = None
    kyc_doc_url: Optional[str] = None
    staff_name: Optional[str] = None
    staff_phone: Optional[str] = None
    reels_count: int = 0
    created_at: datetime
    subscription_status: str = "ACTIVE"
    subscription_start_date: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None
    is_subscription_active: bool = True
    effective_subscription_status: Optional[str] = None


class AdminMerchantSubscriptionUpdateRequest(BaseModel):
    subscription_status: Optional[SubscriptionStatus] = None
    subscription_expires_at: Optional[datetime] = None

    @field_validator("subscription_status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper in SubscriptionStatus.__members__:
                return SubscriptionStatus[v_upper]
        return v

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "AdminMerchantSubscriptionUpdateRequest":
        if self.subscription_status is None and self.subscription_expires_at is None:
            raise ValueError("At least one of subscription_status or subscription_expires_at must be provided.")
        return self


class AdminMerchantSubscriptionExtendRequest(BaseModel):
    duration_days: Optional[int] = Field(None, ge=0)
    months: Optional[int] = Field(None, ge=0)


class AdminMerchantSubscriptionResponse(BaseModel):
    merchant_id: uuid.UUID
    id: Optional[uuid.UUID] = None
    subscription_status: str
    subscription_start_date: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None
    is_subscription_active: bool = True
    effective_subscription_status: Optional[str] = None

    @model_validator(mode="after")
    def sync_id(self) -> "AdminMerchantSubscriptionResponse":
        if self.id is None:
            self.id = self.merchant_id
        return self


class AdminMerchantCreateRequest(BaseModel):
    owner_phone: str = Field(..., description="Registered owner phone +91XXXXXXXXXX")
    business_name: str = Field(..., min_length=2, max_length=150)
    sector: str = Field("FOOD", description="FOOD, FASHION, FOOTWEAR, ELECTRONICS, REAL_ESTATE")
    address_text: str = Field(..., min_length=5)
    city: str = Field("Nagpur", description="Nagpur or Mumbai")
    latitude: float = Field(21.1458)
    longitude: float = Field(79.0882)
    gstin: Optional[str] = None
    shop_act: Optional[str] = None
    udyam: Optional[str] = None
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
    shop_act: Optional[str] = None
    udyam: Optional[str] = None
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
    auto_approve_kyc: Optional[bool] = None
    auto_trial_enabled: Optional[bool] = None
    auto_trial_duration_days: Optional[int] = Field(None, ge=1, le=3650, description="Default trial duration in days")
