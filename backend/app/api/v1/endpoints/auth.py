import uuid
from typing import Annotated, Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
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

    return user


@router.post("/auth/otp/send", response_model=ResponseEnvelope[OtpSendResponse])
async def send_otp(request: OtpSendRequest):
    """Sends a 6-digit OTP to the Indian mobile number (+91)."""
    success, test_otp, msg = await OtpService.send_otp(request.phone, request.channel)
    if not success:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)

    response_data = OtpSendResponse(
        phone=request.phone,
        expires_in_seconds=120,
        test_otp=test_otp
    )
    return ResponseEnvelope(data=response_data, message=msg)


@router.post("/auth/otp/verify", response_model=ResponseEnvelope[AuthTokenResponse])
async def verify_otp(request: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verifies the 6-digit OTP and returns signed JWT access & refresh tokens."""
    data = await AuthService.verify_otp_and_login(
        phone=request.phone,
        otp=request.otp,
        preferred_language=request.preferred_language,
        db=db
    )
    return ResponseEnvelope(data=data, message="Authentication successful")


@router.post("/auth/staff-login", response_model=ResponseEnvelope[StaffLoginResponse])
async def staff_login(request: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    """Cashier/Staff terminal login using merchant phone and 6-digit staff PIN."""
    data = await AuthService.staff_login(request, db)
    return ResponseEnvelope(data=data, message="Staff terminal authenticated")


@router.post("/auth/admin-login", response_model=ResponseEnvelope[AuthTokenResponse])
async def admin_login(request: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    """Super Admin login using master credentials or registered admin account."""
    data = await AuthService.admin_login(request, db)
    return ResponseEnvelope(data=data, message="Super Admin authenticated")


@router.post("/auth/refresh", response_model=ResponseEnvelope[RefreshTokenResponse])
async def refresh_tokens(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Rotates refresh token and returns a new access & refresh token pair."""
    data = await AuthService.refresh_tokens(request.refresh_token, db)
    return ResponseEnvelope(data=data, message="Token refreshed successfully")


@router.post("/auth/logout", response_model=ResponseEnvelope[dict])
async def logout(
    request: Optional[LogoutRequest] = None,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)] = None
):
    """Revokes active refresh token and terminates session."""
    if request and request.refresh_token:
        await SessionService.revoke_refresh_session(request.refresh_token)
    return ResponseEnvelope(data={"logged_out": True}, message="Logged out successfully")


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
