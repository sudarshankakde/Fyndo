import uuid
from typing import Annotated, Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.context import set_user_id
from app.core.database import get_db
from app.core.security import decode_access_token
from dataclasses import dataclass
from app.models.merchant import Merchant, MerchantStaff
from app.models.user import User
from app.schemas.auth import (
    AdminLoginRequest,
    AuthTokenResponse,
    DevTokenRequest,
    DevTokenResponse,
    LogoutRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    StaffLoginRequest,
    StaffLoginResponse,
    UserOut,
    UserProfileUpdateRequest,
)
from app.schemas.common import ResponseEnvelope
from app.services.auth_service import AuthService
from app.services.otp import OtpService
from app.services.session_service import SessionService

router = APIRouter()
security_bearer = HTTPBearer(auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, subject_id: uuid.UUID, role: str, claims: Dict[str, Any]):
        self.subject_id = subject_id
        self.role = role
        self.claims = claims


async def get_auth_context(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)]
) -> AuthContext:
    """Dependency that decodes and validates access token for either User or Staff."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token."
        )

    return AuthContext(
        subject_id=uuid.UUID(payload["sub"]),
        role=payload.get("role", "SHOPPER"),
        claims=payload
    )


@dataclass
class MerchantScope:
    merchant_id: uuid.UUID
    staff_id: Optional[uuid.UUID] = None


async def get_merchant_scope(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> MerchantScope:
    """Resolves merchant scope for either store owner or assigned cashier."""
    if auth.role == "ROLE_CASHIER":
        claim_mid = auth.claims.get("merchant_id")
        if not claim_mid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing merchant scope."
            )
        try:
            claim_mid_uuid = uuid.UUID(str(claim_mid))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid merchant identifier in token."
            )

        staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.id == auth.subject_id))
        staff = staff_res.scalars().first()
        if not staff or not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff account inactive or not found."
            )
        if staff.merchant_id != claim_mid_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff POS credentials do not belong to the claimed merchant."
            )
        return MerchantScope(merchant_id=staff.merchant_id, staff_id=staff.id)

    # Owner token
    result = await db.execute(select(Merchant).where(Merchant.user_id == auth.subject_id))
    merchant = result.scalars().first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant profile not found for this user."
        )
    return MerchantScope(merchant_id=merchant.id, staff_id=None)


async def get_current_user(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency that authenticates the user via JWT bearer token."""
    if auth.role == "ROLE_CASHIER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff POS credentials cannot be used for user account actions."
        )

    result = await db.execute(select(User).where(User.id == auth.subject_id))
    user = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or suspended."
        )

    set_user_id(user.id)
    return user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(optional_bearer)],
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Resolves the caller when a bearer token is present, otherwise None.

    Used by public endpoints (feed, reel detail, view counting) that still
    personalise their response for signed-in shoppers.
    """
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload or payload.get("role") == "ROLE_CASHIER":
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        return None
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalars().first()
    if user:
        set_user_id(user.id)
    return user


@router.post("/auth/otp/send", response_model=ResponseEnvelope[OtpSendResponse])
async def send_otp(request: OtpSendRequest, db: AsyncSession = Depends(get_db)):
    """Sends a 6-digit OTP to the Indian mobile number (+91)."""
    await AuthService.validate_role_eligibility(request.phone, request.role, db)

    success, test_otp, msg = await OtpService.send_otp(request.phone, request.channel)
    if not success:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    response_data = OtpSendResponse(
        phone=request.phone,
        expires_in_seconds=120,
        test_otp=test_otp if settings.ENVIRONMENT.lower() != "production" else None
    )
    return ResponseEnvelope(data=response_data, message=msg)


@router.post("/auth/otp/verify", response_model=ResponseEnvelope[AuthTokenResponse])
async def verify_otp(request: OtpVerifyRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Verifies the 6-digit OTP and returns signed JWT access & refresh tokens."""
    data = await AuthService.verify_otp_and_login(
        phone=request.phone,
        otp=request.otp,
        preferred_language=request.preferred_language,
        db=db,
        role=request.role
    )
    _set_refresh_cookie(response, data.refresh_token)
    return ResponseEnvelope(data=data, message="Authentication successful")


@router.post("/auth/staff-login", response_model=ResponseEnvelope[StaffLoginResponse])
@router.post("/auth/staff-pin", response_model=ResponseEnvelope[StaffLoginResponse])
async def staff_login(request: StaffLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Cashier/Staff terminal login using merchant phone and 6-digit staff PIN."""
    data = await AuthService.staff_login(request, db)
    if data.refresh_token:
        _set_refresh_cookie(response, data.refresh_token)
    return ResponseEnvelope(data=data, message="Staff terminal authenticated")



@router.post("/auth/admin-login", response_model=ResponseEnvelope[AuthTokenResponse])
async def admin_login(request: AdminLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Super Admin login using master credentials or registered admin account."""
    data = await AuthService.admin_login(request, db)
    _set_refresh_cookie(response, data.refresh_token)
    return ResponseEnvelope(data=data, message="Super Admin authenticated")


@router.post("/auth/refresh", response_model=ResponseEnvelope[RefreshTokenResponse])
async def refresh_tokens(
    request: RefreshTokenRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Rotates refresh token and returns a new access & refresh token pair."""
    token = request.refresh_token or http_request.cookies.get("fyndo_refresh_token") or ""
    data = await AuthService.refresh_tokens(token, db)
    _set_refresh_cookie(response, data.refresh_token)
    return ResponseEnvelope(data=data, message="Token refreshed successfully")


@router.post("/auth/logout", response_model=ResponseEnvelope[dict])
async def logout(
    http_request: Request,
    response: Response,
    request: Optional[LogoutRequest] = None,
):
    """Revokes active refresh token and terminates session."""
    refresh_token = (
        request.refresh_token
        if request and request.refresh_token
        else http_request.cookies.get("fyndo_refresh_token")
    )
    if refresh_token:
        await SessionService.revoke_refresh_session(refresh_token)
    response.delete_cookie("fyndo_refresh_token", path=f"{settings.API_V1_STR}/auth")
    return ResponseEnvelope(data={"logged_out": True}, message="Logged out successfully")


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="fyndo_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="strict" if settings.ENVIRONMENT.lower() == "production" else "lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=f"{settings.API_V1_STR}/auth",
    )


@router.get("/auth/me", response_model=ResponseEnvelope[UserOut])
async def get_me(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db)
):
    """Returns currently authenticated user or staff profile."""
    profile = await AuthService.get_profile(auth.subject_id, auth.role, db)
    return ResponseEnvelope(data=profile)


@router.patch("/auth/profile", response_model=ResponseEnvelope[UserOut])
async def update_profile(
    request: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates profile information for the authenticated user."""
    updated = await AuthService.update_profile(current_user, request, db)
    return ResponseEnvelope(data=updated, message="Profile updated successfully")


@router.post("/auth/dev-token", response_model=ResponseEnvelope[DevTokenResponse])
async def create_dev_token(request: DevTokenRequest, db: AsyncSession = Depends(get_db)):
    """Fast-lane token generation for frontend development and automated tests."""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development token generation is disabled in production."
        )
    data = await AuthService.create_dev_token(request.role, request.phone, db)
    return ResponseEnvelope(data=data, message=f"Development token generated for {request.role}")
