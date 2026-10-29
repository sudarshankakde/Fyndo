import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
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
    async def validate_role_eligibility(
        cls,
        phone: str,
        role: Optional[str],
        db: AsyncSession,
    ) -> None:
        """Validates that a phone number is eligible for the requested role (shopper vs merchant)."""
        if not role:
            return

        norm_role = role.strip().lower()
        if norm_role not in ("shopper", "customer", "merchant", "cashier", "staff"):
            return

        if norm_role in ("cashier", "staff"):
            staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.phone == phone))
            staff = staff_res.scalars().first()
            if not staff:
                user_res = await db.execute(select(User).where(User.phone == phone))
                owner = user_res.scalars().first()
                if owner:
                    merch_res = await db.execute(select(Merchant).where(Merchant.user_id == owner.id))
                    merchant = merch_res.scalars().first()
                    if merchant:
                        staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id))
                        staff = staff_res.scalars().first()
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No registered store or counter staff found for this mobile number.",
                )
            return

        stmt = select(User).where(User.phone == phone)
        res = await db.execute(stmt)
        user = res.scalars().first()
        if not user:
            # Phone is not registered; new shopper or new merchant registration is allowed
            return

        # Determine if user is registered as a merchant
        is_merchant = False
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role_str == "MERCHANT":
            is_merchant = True
        else:
            merch_stmt = select(Merchant).where(Merchant.user_id == user.id)
            merch_res = await db.execute(merch_stmt)
            if merch_res.scalars().first():
                is_merchant = True

        if norm_role in ("shopper", "customer"):
            if is_merchant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This phone number is registered as a Merchant account. Please sign in through Merchant Login.",
                )
        elif norm_role == "merchant":
            # An existing merchant (is_merchant == True) or an existing customer without
            # a store record (is_merchant == False) is allowed to authenticate and onboard.
            # Role upgrade to MERCHANT occurs only upon successful onboarding submission.
            pass


    @classmethod
    async def verify_otp_and_login(
        cls,
        phone: str,
        otp: str,
        preferred_language: str,
        db: AsyncSession,
        role: Optional[str] = None,
    ) -> AuthTokenResponse:
        """Verifies 6-digit OTP and authenticates/upserts shopper or merchant user."""
        await cls.validate_role_eligibility(phone, role, db)

        is_valid = await OtpService.verify_otp(phone, otp)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 6-digit OTP entered is incorrect or expired."
            )

        stmt = select(User).where(User.phone == phone)
        res = await db.execute(stmt)
        user = res.scalars().first()

        norm_role = role.strip().lower() if role else None
        target_role = UserRole.MERCHANT if norm_role == "merchant" else UserRole.SHOPPER

        if not user:
            user = User(
                phone=phone,
                role=target_role,
                preferred_language=preferred_language or "en",
                onboarding_completed=False,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
        else:
            if norm_role == "merchant" and user.role != UserRole.MERCHANT:
                user.role = UserRole.MERCHANT
                await db.flush()

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
        """Authenticates cashier staff via store owner phone or staff phone and 6-digit PIN."""
        raw_phone = request.store_phone or request.phone
        if not raw_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Store phone or staff mobile number is required."
            )

        lookup_phone = raw_phone.strip().replace(" ", "")
        if not lookup_phone.startswith("+91"):
            lookup_phone = f"+91{lookup_phone}"

        # 1. Try finding staff directly by staff's phone
        staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.phone == lookup_phone))
        staff = staff_res.scalars().first()

        merchant = None
        if staff:
            merch_res = await db.execute(select(Merchant).where(Merchant.id == staff.merchant_id))
            merchant = merch_res.scalars().first()
        else:
            # 2. Try finding merchant by owner's phone
            user_res = await db.execute(select(User).where(User.phone == lookup_phone))
            owner = user_res.scalars().first()
            if owner:
                merch_res = await db.execute(select(Merchant).where(Merchant.user_id == owner.id))
                merchant = merch_res.scalars().first()
                if merchant:
                    staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id))
                    staff = staff_res.scalars().first()

        if not merchant or not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registered store or counter staff found for this mobile number."
            )

        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No active counter staff assigned to this store."
            )

        if not verify_password(request.pin, staff.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The 6-digit staff PIN entered is incorrect."
            )

        if request.otp:
            is_valid = await OtpService.verify_otp(lookup_phone, request.otp)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The 6-digit OTP entered is incorrect or expired."
                )


        can_upload = bool(staff.can_upload_reels)
        can_manage = bool(getattr(staff, "can_manage_content", False))

        token = create_access_token(
            subject=str(staff.id),
            role="ROLE_CASHIER",
            extra_claims={
                "merchant_id": str(merchant.id),
                "business_name": merchant.business_name,
                "can_upload_reels": can_upload,
                "can_manage_content": can_manage,
            }
        )
        ref_token = create_refresh_token(
            subject=str(staff.id),
            role="ROLE_CASHIER",
            extra_claims={
                "merchant_id": str(merchant.id),
                "business_name": merchant.business_name,
                "can_upload_reels": can_upload,
                "can_manage_content": can_manage,
            },
        )
        await SessionService.store_refresh_session(ref_token, str(staff.id), "ROLE_CASHIER")

        user_out = UserOut(
            id=staff.id,
            phone=staff.phone,
            full_name=staff.staff_name,
            role="ROLE_CASHIER",
            preferred_language="en",
            merchant_id=merchant.id,
            business_name=merchant.business_name,
            kyc_status=merchant.kyc_status.value if hasattr(merchant.kyc_status, "value") else str(merchant.kyc_status),
            can_upload_reels=can_upload,
            can_manage_content=can_manage,
        )

        return StaffLoginResponse(
            access_token=token,
            refresh_token=ref_token,
            staff_id=staff.id,
            staff_name=staff.staff_name,
            merchant_id=merchant.id,
            business_name=merchant.business_name,
            can_upload_reels=can_upload,
            can_manage_content=can_manage,
            user=user_out
        )


    @classmethod
    async def admin_login(cls, request: AdminLoginRequest, db: AsyncSession) -> AuthTokenResponse:
        """Authenticates Super Admin via admin credentials."""
        identifier = request.identifier.strip()
        is_master = settings.ENVIRONMENT.lower() != "production" and (
            (
                identifier == settings.SUPER_ADMIN_IDENTIFIER
                or identifier.lower() == (settings.SUPER_ADMIN_EMAIL or "").lower()
            )
            and request.password == settings.SUPER_ADMIN_PASSWORD
        )

        clean_id = identifier.lower()
        admin_email = (settings.SUPER_ADMIN_EMAIL or "").lower().strip()
        admin_phone = settings.SUPER_ADMIN_IDENTIFIER.strip()

        if clean_id in (admin_email, admin_phone.lower()):
            stmt = select(User).where(
                (User.phone == admin_phone)
                | (func.lower(User.email) == admin_email)
                | (User.phone == identifier)
                | (func.lower(User.email) == clean_id)
            )
        else:
            stmt = select(User).where(
                (User.phone == identifier) | (func.lower(User.email) == clean_id)
            )
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
            if is_master:
                if not user.email and settings.SUPER_ADMIN_EMAIL:
                    user.email = settings.SUPER_ADMIN_EMAIL
                if not user.password_hash and settings.SUPER_ADMIN_PASSWORD:
                    user.password_hash = get_password_hash(settings.SUPER_ADMIN_PASSWORD)
                user.role = UserRole.SUPER_ADMIN
                await db.flush()
        else:
            if not is_master:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid administrator credentials."
                )
            existing_phone = (
                await db.execute(select(User).where(User.phone == admin_phone))
            ).scalars().first()
            if existing_phone:
                user = existing_phone
                user.email = settings.SUPER_ADMIN_EMAIL
                user.role = UserRole.SUPER_ADMIN
                user.password_hash = get_password_hash(settings.SUPER_ADMIN_PASSWORD)
            else:
                user = User(
                    phone=settings.SUPER_ADMIN_IDENTIFIER,
                    email=settings.SUPER_ADMIN_EMAIL,
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
            staff_res = await db.execute(
                select(MerchantStaff)
                .options(selectinload(MerchantStaff.merchant))
                .where(MerchantStaff.id == uuid.UUID(user_id_str))
            )
            staff = staff_res.scalars().first()
            if not staff or not staff.is_active or not staff.merchant:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff account inactive.")
            new_access = create_access_token(
                subject=user_id_str,
                role=role,
                extra_claims={
                    "merchant_id": str(staff.merchant_id),
                    "business_name": staff.merchant.business_name,
                },
            )
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
                business_name=staff.merchant.business_name if staff.merchant else None,
                kyc_status=staff.merchant.kyc_status.value if (staff.merchant and hasattr(staff.merchant.kyc_status, "value")) else (str(staff.merchant.kyc_status) if staff.merchant else None),
                can_upload_reels=bool(staff.can_upload_reels),
                can_manage_content=bool(getattr(staff, "can_manage_content", False)),
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
        if payload.username is not None:
            username = payload.username.strip().lower()
            existing = (await db.execute(
                select(User).where(User.username == username, User.id != user.id)
            )).scalars().first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="That username is already taken.",
                )
            user.username = username
        if payload.profile_image_url is not None:
            user.profile_image_url = payload.profile_image_url.strip() or None
        if payload.email is not None:
            user.email = payload.email.strip()
        if payload.preferred_language is not None:
            user.preferred_language = payload.preferred_language.strip().lower()

        # Shopper location fields
        loc_changed = False
        if payload.latitude is not None:
            user.latitude = payload.latitude
            loc_changed = True
        if payload.longitude is not None:
            user.longitude = payload.longitude
            loc_changed = True
        if payload.city is not None:
            user.city = payload.city.strip()
            loc_changed = True
        if payload.address_text is not None:
            user.address_text = payload.address_text.strip()
            loc_changed = True
        if payload.pincode is not None:
            user.pincode = payload.pincode.strip()
        if loc_changed:
            user.location_updated_at = datetime.now(timezone.utc)

        # Shopper category preferences
        if payload.shopping_preferences is not None:
            cleaned = [p.strip() for p in payload.shopping_preferences if isinstance(p, str) and p.strip()]
            user.shopping_preferences = json.dumps(cleaned)

        # Check completeness for shoppers
        if user.role == UserRole.SHOPPER:
            has_name = bool(user.full_name and len(user.full_name.strip()) >= 2)
            has_prefs = False
            if user.shopping_preferences:
                try:
                    prefs = json.loads(user.shopping_preferences)
                    has_prefs = bool(isinstance(prefs, list) and len(prefs) >= 1)
                except Exception:
                    has_prefs = False
            has_loc = bool(
                user.latitude is not None
                and user.longitude is not None
                and bool(user.city and user.city.strip())
                and bool(user.address_text and user.address_text.strip())
            )
            if has_name and has_prefs and has_loc:
                user.onboarding_completed = True

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
