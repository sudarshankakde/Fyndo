import uuid
from typing import Optional
from pydantic import BaseModel, Field


class ModerationDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE or REJECT")
    rejection_reason: Optional[str] = None


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
