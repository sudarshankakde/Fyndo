import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CouponCreateEmbedded(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    discount_type: str = Field("PERCENTAGE", description="PERCENTAGE, FLAT/FLAT_AMOUNT, BOGO")
    discount_value: float = Field(..., gt=0)
    min_order_amount: float = Field(0.0, ge=0)
    validity_days: int = Field(5, gt=0)
    terms: Optional[str] = None

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, v: str) -> str:
        val = v.upper()
        if val in {"FLAT", "FLAT_AMOUNT"}:
            return "FLAT_AMOUNT"
        if val in {"PERCENTAGE", "BOGO"}:
            return val
        return "PERCENTAGE"


class ReelCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    video_url: str = Field(..., min_length=5)
    thumbnail_url: Optional[str] = Field(
        default="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80",
        description="Thumbnail image URL"
    )
    cloudinary_public_id: Optional[str] = None
    duration_seconds: int = Field(30, ge=5, le=180)
    audio_type: str = Field("CAMERA_MIC", description="CAMERA_MIC or VOICEOVER")
    allow_comments: bool = Field(True, description="Enable or disable customer comments")
    coupon: CouponCreateEmbedded

    @field_validator("audio_type")
    @classmethod
    def validate_audio(cls, v: str) -> str:
        val = v.upper()
        if val in {"ORIGINAL_CAMERA", "CAMERA_MIC", "ORIGINAL", "RAW"}:
            return "CAMERA_MIC"
        if val in {"VOICEOVER", "MIC"}:
            return "VOICEOVER"
        return "CAMERA_MIC"



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
    likes_count: int = 0
    is_liked: bool = False
    allow_comments: bool = True
    comments_count: int = 0
    merchant: MerchantFeedSummary
    coupon: Optional[CouponFeedSummary] = None

    model_config = {"from_attributes": True}


class ReelCommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    parent_comment_id: Optional[uuid.UUID] = None


class ReelCommentOut(BaseModel):
    id: uuid.UUID
    parent_comment_id: Optional[uuid.UUID] = None
    user_name: str
    user_initial: str
    profile_image_url: Optional[str] = None
    text: str
    created_at: datetime
    is_store_reply: bool = False


class ReelManagementOut(BaseModel):
    id: uuid.UUID
    title: str
    video_url: str
    thumbnail_url: str
    duration_seconds: int
    status: str
    rejection_reason: Optional[str] = None
    views_count: int
    allow_comments: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class ReelUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    video_url: Optional[str] = Field(None, min_length=5)
    thumbnail_url: Optional[str] = Field(None, min_length=5)
    allow_comments: Optional[bool] = None
