import uuid
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CouponCreateEmbedded(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    discount_type: str = Field(..., description="PERCENTAGE, FLAT_AMOUNT, BOGO")
    discount_value: float = Field(..., gt=0)
    min_order_amount: float = Field(0.0, ge=0)
    validity_days: int = Field(..., gt=0)
    terms: Optional[str] = None


class ReelCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    video_url: str = Field(..., min_length=10)
    thumbnail_url: str = Field(..., min_length=10)
    cloudinary_public_id: Optional[str] = None
    duration_seconds: int = Field(..., ge=15, le=60)
    audio_type: str = Field("CAMERA_MIC", description="CAMERA_MIC or VOICEOVER")
    coupon: CouponCreateEmbedded

    @field_validator("audio_type")
    @classmethod
    def validate_audio(cls, v: str) -> str:
        if v.upper() not in {"CAMERA_MIC", "VOICEOVER"}:
            raise ValueError("Audio must be strictly CAMERA_MIC or VOICEOVER (No copyrighted music allowed)")
        return v.upper()


class MerchantFeedSummary(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    address: str
    distance_meters: int


class CouponFeedSummary(BaseModel):
    id: uuid.UUID
    title: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    validity_days: int


class ReelOut(BaseModel):
    id: uuid.UUID
    title: str
    video_url: str
    thumbnail_url: str
    duration_seconds: int
    views_count: int
    merchant: MerchantFeedSummary
    coupon: Optional[CouponFeedSummary] = None

    model_config = {"from_attributes": True}
