import uuid
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OtpSendRequest(BaseModel):
    phone: str = Field(..., description="Indian phone number with country code e.g. +919876543210")
    channel: str = Field("SMS", description="SMS or WHATSAPP")
    role: Optional[str] = Field(None, description="Intended login role: 'shopper' or 'merchant'")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not v.startswith("+91") or len(v) != 13:
            raise ValueError("Phone number must be a valid Indian number formatted as +91XXXXXXXXXX")
        return v


class OtpSendResponse(BaseModel):
    phone: str
    expires_in_seconds: int = 120
    test_otp: Optional[str] = None  # Returned in dev / mock mode


class OtpVerifyRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=6, max_length=6)
    preferred_language: str = Field("en", description="en, hi, or mr")
    role: Optional[str] = Field(None, description="Intended login role: 'shopper' or 'merchant'")


class UserOut(BaseModel):
    id: uuid.UUID
    phone: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    profile_image_url: Optional[str] = None
    email: Optional[str] = None
    role: str
    preferred_language: str = "en"
    merchant_id: Optional[uuid.UUID] = None
    business_name: Optional[str] = None
    kyc_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    address_text: Optional[str] = None
    pincode: Optional[str] = None
    shopping_preferences: Optional[list[str]] = None
    onboarding_completed: bool = False

    model_config = {"from_attributes": True}


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserOut


class StaffLoginRequest(BaseModel):
    store_phone: Optional[str] = Field(None, description="Store owner or staff registered phone number")
    phone: Optional[str] = Field(None, description="Alias for store_phone")
    pin: str = Field(..., min_length=6, max_length=6, description="6-digit staff PIN")


class StaffLoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    staff_id: uuid.UUID
    staff_name: str
    merchant_id: uuid.UUID
    business_name: str
    user: Optional[UserOut] = None



class AdminLoginRequest(BaseModel):
    identifier: str = Field(..., description="Admin phone (+91...) or email address")
    password: str = Field(..., min_length=6, description="Super Admin master password")
    mfa_code: Optional[str] = Field(None, description="Optional 6-digit TOTP MFA code")


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Optional legacy refresh token; secure cookie is preferred")


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Active refresh token to revoke")


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9._]+$")
    profile_image_url: Optional[str] = Field(None, max_length=500)
    email: Optional[str] = Field(None, max_length=255)
    preferred_language: Optional[str] = Field(None, description="en, hi, or mr")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    city: Optional[str] = Field(None, max_length=100)
    address_text: Optional[str] = Field(None, max_length=1000)
    pincode: Optional[str] = Field(None, max_length=20)
    shopping_preferences: Optional[list[str]] = Field(None, description="Category keys/IDs chosen by shopper")


class DevTokenRequest(BaseModel):
    role: str = Field("SHOPPER", description="SHOPPER, MERCHANT, ROLE_CASHIER, or SUPER_ADMIN")
    phone: Optional[str] = Field(None, description="Optional specific phone number")


class DevTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    role: str
    user: UserOut
