import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProfileVideoUpdateRequest(BaseModel):
    profile_video_url: str = Field(..., min_length=5, max_length=500)
    profile_video_thumbnail_url: Optional[str] = Field(None, max_length=500)


class ProfileVideoOut(BaseModel):
    merchant_id: uuid.UUID
    profile_video_url: Optional[str] = None
    profile_video_thumbnail_url: Optional[str] = None


class CallTrackRequest(BaseModel):
    device_fingerprint: Optional[str] = Field(None, max_length=128)


class CallTrackResponse(BaseModel):
    counted: bool


class FollowToggleResponse(BaseModel):
    merchant_id: uuid.UUID
    is_following: bool
    followers_count: int


class FollowedMerchantOut(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    city: str
    address_text: str
    profile_video_thumbnail_url: Optional[str] = None
    followed_at: datetime


class RatingCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = Field(None, max_length=1000)


class RatingOut(BaseModel):
    id: uuid.UUID
    rating: int
    review_text: Optional[str] = None
    user_name: str
    updated_at: datetime


class RatingSummaryOut(BaseModel):
    merchant_id: uuid.UUID
    average: float
    count: int
    breakdown: Dict[str, int]
    my_rating: Optional[int] = None
    reviews: List[RatingOut] = []


class StaffPermissionUpdateRequest(BaseModel):
    can_upload_reels: bool


class MerchantInsightsOut(BaseModel):
    followers_count: int
    call_clicks_total: int
    call_clicks_last_7_days: int
    reel_views_total: int
    rating_average: float
    rating_count: int
