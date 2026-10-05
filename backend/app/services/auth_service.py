import uuid
import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.merchant import Merchant, MerchantStaff
from app.models.user import User, UserRole
from app.schemas.auth import (
    AdminLoginRequest,
    AuthTokenResponse,
    DevTokenResponse,
    RefreshTokenResponse,
    StaffLoginRequest,
    StaffLoginResponse,
    UserOut,
    UserProfileUpdateRequest,
)
from app.services.auth_helpers import build_user_out
from app.services.otp import OtpService
from app.services.session_service import SessionService

logger = logging.getLogger("fyndo.auth_service")


class AuthService:
    """Core domain service for user and staff authentication."""

    @classmethod
    async def verify_otp_and_login(
        cls,
        phone: str,
        otp: str,
        preferred_language: str,
        db: AsyncSession
    ) -> AuthTokenResponse:
        """Verifies 6-digit OTP and authenticates/upserts shopper or merchant user."""
        is_valid = await OtpService.verify_otp(phone, otp)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 6-digit OTP entered is incorrect or expired."
            )

        stmt = select(User).where(User.phone == phone)
        res = await db.execute(stmt)
        user = res.scalars().first()

        if not user:
            user = User(phone=phone, role=UserRole.SHOPPER, preferred_language=preferred_language)
            db.add(user)
            await db.flush()
            await db.refresh(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated or suspended."
            )

        role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        access_token = create_access_token(
            subject=str(user.id),
            role=role_str,
            extra_claims={"phone": user.phone}
        )
        refresh_token = create_refresh_token(subject=str(user.id), role=role_str)
        await SessionService.store_refresh_session(refresh_token, str(user.id), role_str)

        user_out = await build_user_out(user, db)
        return AuthTokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_out)

    @classmethod
    async def staff_login(cls, request: StaffLoginRequest, db: AsyncSession) -> StaffLoginResponse:
        """Authenticates cashier staff via store phone and 6-digit PIN."""
        user_res = await db.execute(select(User).where(User.phone == request.store_phone))
        owner = user_res.scalars().first()
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store account not found for this mobile number."
            )

        merch_res = await db.execute(select(Merchant).where(Merchant.user_id == owner.id))
        merchant = merch_res.scalars().first()
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant profile not registered for this store."
            )

        staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id))
        staff = staff_res.scalars().first()
        if not staff or not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No active counter staff assigned to this store."
            )

        if not verify_password(request.pin, staff.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The 6-digit staff PIN entered is incorrect."
            )

        token = create_access_token(
            subject=str(staff.id),
            role="ROLE_CASHIER",
            extra_claims={"merchant_id": str(merchant.id), "business_name": merchant.business_name}
        )
        ref_token = create_refresh_token(subject=str(staff.id), role="ROLE_CASHIER")
        await SessionService.store_refresh_session(ref_token, str(staff.id), "ROLE_CASHIER")

        return StaffLoginResponse(
            access_token=token,
            refresh_token=ref_token,
            staff_id=staff.id,
            staff_name=staff.staff_name,
            merchant_id=merchant.id,
            business_name=merchant.business_name
        )

    @classmethod
    async def admin_login(cls, request: AdminLoginRequest, db: AsyncSession) -> AuthTokenResponse:
        """Authenticates Super Admin via admin credentials."""
        identifier = request.identifier.strip()
        is_master = (
            (identifier == settings.SUPER_ADMIN_IDENTIFIER or identifier == "admin@fyndo.in")
            and request.password == settings.SUPER_ADMIN_PASSWORD
        )

        stmt = select(User).where((User.phone == identifier) | (User.email == identifier))
        res = await db.execute(stmt)
        user = res.scalars().first()

        if user:
            if user.role != UserRole.SUPER_ADMIN and not is_master:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This account does not have Super Admin privileges."
                )
            valid_pwd = (
                (user.password_hash and verify_password(request.password, user.password_hash))
                or is_master
            )
            if not valid_pwd:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid administrator credentials."
                )
        else:
            if not is_master:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid administrator credentials."
                )
            user = User(
                phone=settings.SUPER_ADMIN_IDENTIFIER,
                email="admin@fyndo.in",
                full_name="Regional Desk Admin",
                role=UserRole.SUPER_ADMIN,
                password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD),
                preferred_language="en"
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)

        access_token = create_access_token(
            subject=str(user.id),
            role="SUPER_ADMIN",
            extra_claims={"phone": user.phone, "email": user.email}
        )
        refresh_token = create_refresh_token(subject=str(user.id), role="SUPER_ADMIN")
        await SessionService.store_refresh_session(refresh_token, str(user.id), "SUPER_ADMIN")

        user_out = await build_user_out(user, db)
        return AuthTokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_out)

    @classmethod
    async def refresh_tokens(cls, token: str, db: AsyncSession) -> RefreshTokenResponse:
        """Rotates refresh token and issues a new access/refresh token pair."""
        payload = decode_refresh_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

        session_data = await SessionService.validate_refresh_session(token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or token revoked. Please log in again."
            )

        user_id_str = payload["sub"]
        role = payload.get("role", "SHOPPER")

        if role == "ROLE_CASHIER":
            new_access = create_access_token(subject=user_id_str, role=role)
        else:
            user_id = uuid.UUID(user_id_str)
            res = await db.execute(select(User).where(User.id == user_id))
            user = res.scalars().first()
            if not user or not user.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account inactive.")
            new_access = create_access_token(subject=str(user.id), role=role, extra_claims={"phone": user.phone})

        new_refresh = create_refresh_token(subject=user_id_str, role=role)
        await SessionService.rotate_refresh_session(token, new_refresh, user_id_str, role)

        return RefreshTokenResponse(access_token=new_access, refresh_token=new_refresh)

    @classmethod
    async def get_profile(cls, subject_id: uuid.UUID, role: str, db: AsyncSession) -> UserOut:
        """Resolves full authenticated profile for User or Staff."""
        if role == "ROLE_CASHIER":
            res = await db.execute(
                select(MerchantStaff)
                .options(selectinload(MerchantStaff.merchant))
                .where(MerchantStaff.id == subject_id)
            )
            staff = res.scalars().first()
            if not staff:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff account not found.")

            return UserOut(
                id=staff.id,
                phone=staff.phone,
                full_name=staff.staff_name,
                role="ROLE_CASHIER",
                preferred_language="en",
                merchant_id=staff.merchant_id,
                business_name=staff.merchant.business_name if staff.merchant else None
            )

        res = await db.execute(select(User).where(User.id == subject_id))
        user = res.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

        return await build_user_out(user, db)

    @classmethod
    async def update_profile(cls, user: User, payload: UserProfileUpdateRequest, db: AsyncSession) -> UserOut:
        """Updates user profile information."""
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.email is not None:
            user.email = payload.email.strip()
        if payload.preferred_language is not None:
            user.preferred_language = payload.preferred_language.strip().lower()

        await db.flush()
        await db.refresh(user)
        return await build_user_out(user, db)

    @classmethod
    async def create_dev_token(cls, role: str, phone: Optional[str], db: AsyncSession) -> DevTokenResponse:
        """Mints immediate development tokens for testing all platform roles."""
        role_upper = role.upper()
        if role_upper not in ["SHOPPER", "MERCHANT", "ROLE_CASHIER", "SUPER_ADMIN"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {role}")

        target_phone = phone or (
            "+919876543210" if role_upper in ["SHOPPER", "MERCHANT"]
            else "+919999900000" if role_upper == "SUPER_ADMIN"
            else "+919876543219"
        )

        res = await db.execute(select(User).where(User.phone == target_phone))
        user = res.scalars().first()
        if not user:
            assigned_role = (
                UserRole.SUPER_ADMIN if role_upper == "SUPER_ADMIN"
                else UserRole.MERCHANT if role_upper == "MERCHANT"
                else UserRole.SHOPPER
            )
            user = User(phone=target_phone, full_name=f"Demo {role_upper.title()} User", role=assigned_role)
            db.add(user)
            await db.flush()
            await db.refresh(user)

        user_id_str = str(user.id)
        access_token = create_access_token(subject=user_id_str, role=role_upper, extra_claims={"phone": user.phone})
        refresh_token = create_refresh_token(subject=user_id_str, role=role_upper)
        await SessionService.store_refresh_session(refresh_token, user_id_str, role_upper)
        user_out = await build_user_out(user, db)

        return DevTokenResponse(access_token=access_token, refresh_token=refresh_token, role=role_upper, user=user_out)
