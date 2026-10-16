import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class MerchantOnboardRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=150)
    sector: str = Field(..., description="FOOD, FASHION, FOOTWEAR, ELECTRONICS, REAL_ESTATE")
    address_text: str = Field(..., min_length=5)
    city: str = Field(..., description="Nagpur or Mumbai")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    gstin: Optional[str] = None
    kyc_doc_url: str = Field(..., min_length=10)

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str) -> str:
        valid_sectors = {"FOOD", "FASHION", "FOOTWEAR", "ELECTRONICS", "REAL_ESTATE"}
        if v.upper() not in valid_sectors:
            raise ValueError(f"Invalid sector: {v}. Must be one of {valid_sectors}")
        return v.upper()


class MerchantOut(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str
    address_text: str
    city: str
    latitude: float
    longitude: float
    kyc_status: str

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

    model_config = {"from_attributes": True}


class StaffUpdateRequest(BaseModel):
    staff_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    pin: Optional[str] = Field(None, min_length=6, max_length=6)
    is_active: Optional[bool] = None


class MerchantProfileUpdateRequest(BaseModel):
    business_name: Optional[str] = Field(None, min_length=2, max_length=150)
    address_text: Optional[str] = Field(None, min_length=5)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    gstin: Optional[str] = Field(None, max_length=20)


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
