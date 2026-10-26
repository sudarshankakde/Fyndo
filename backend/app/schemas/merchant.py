import json
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class MerchantOnboardRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=150)
    sector: str = Field(..., description="Store category or type")
    address_text: str = Field(..., min_length=5)
    city: str = Field(..., description="Nagpur, Mumbai, etc.")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    gstin: Optional[str] = None
    kyc_doc_url: str = Field(..., min_length=10)
    cover_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str) -> str:
        from app.services.category_assets import normalize_sector, VALID_SECTORS
        normalized = normalize_sector(v)
        if normalized not in VALID_SECTORS and v.upper() not in VALID_SECTORS:
            raise ValueError(f"Invalid sector: {v}")
        return v.upper()


class CategoryMetaOut(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    sub_categories: List[str] = []
    cover_url: Optional[str] = None
    logo_url: Optional[str] = None


class MerchantOut(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    sub_categories: Optional[List[str]] = None
    address_text: str
    city: str
    latitude: float
    longitude: float
    kyc_status: str
    gstin: Optional[str] = None
    kyc_doc_url: Optional[str] = None
    kyc_rejection_reason: Optional[str] = None
    profile_video_url: Optional[str] = None
    profile_video_thumbnail_url: Optional[str] = None
    cover_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    business_hours: Optional[str] = None
    call_clicks_count: int = 0
    created_at: Optional[datetime] = None

    @field_validator("sub_categories", mode="before")
    @classmethod
    def parse_sub_categories(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [s.strip() for s in v.split(",") if s.strip()]
        return []

    model_config = {"from_attributes": True}


class StaffCreateRequest(BaseModel):
    staff_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    pin: str = Field(..., min_length=6, max_length=6, description="6-digit cashier POS PIN")


class StaffOut(BaseModel):
    id: uuid.UUID
    staff_name: str
    phone: str
    is_active: bool
    can_upload_reels: bool = False

    model_config = {"from_attributes": True}


class StaffUpdateRequest(BaseModel):
    staff_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    pin: Optional[str] = Field(None, min_length=6, max_length=6)
    is_active: Optional[bool] = None


class MerchantProfileUpdateRequest(BaseModel):
    business_name: Optional[str] = Field(None, min_length=2, max_length=150)
    sector: Optional[str] = None
    address_text: Optional[str] = Field(None, min_length=5)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    gstin: Optional[str] = Field(None, max_length=20)
    cover_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    business_hours: Optional[str] = None
    sub_categories: Optional[List[str]] = None


class MerchantKycResubmissionRequest(BaseModel):
    business_name: Optional[str] = Field(None, min_length=2, max_length=150)
    address_text: Optional[str] = Field(None, min_length=5)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    gstin: Optional[str] = Field(None, max_length=20)
    kyc_doc_url: Optional[str] = Field(None, min_length=10)


class PublicMerchantOut(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    address_text: str
    city: str
    latitude: float
    longitude: float
    profile_video_url: Optional[str] = None
    profile_video_thumbnail_url: Optional[str] = None
    cover_url: Optional[str] = None
    logo_url: Optional[str] = None
    followers_count: int = 0
    is_following: bool = False
    rating_average: float = 0.0
    rating_count: int = 0


class AdminMerchantKycItem(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    city: str
    kyc_doc_url: str
    kyc_status: str
    kyc_rejection_reason: Optional[str] = None
    owner_phone: str
    submitted_at: datetime


class MerchantDraftSaveRequest(BaseModel):
    step: int = Field(1, ge=1, le=3)
    business_name: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    address_text: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gstin: Optional[str] = None
    kyc_doc_url: Optional[str] = None


class MerchantDraftOut(BaseModel):
    has_draft: bool
    step: int = 1
    business_name: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    address_text: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gstin: Optional[str] = None
    kyc_doc_url: Optional[str] = None
    updated_at: Optional[datetime] = None

