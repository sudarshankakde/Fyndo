import json
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.merchant import Merchant
from app.models.user import User, UserRole
from app.schemas.auth import UserOut


async def build_user_out(user: User, db: AsyncSession) -> UserOut:
    """Helper to convert User model into UserOut schema with merchant details."""
    merchant_id: Optional[uuid.UUID] = None
    business_name: Optional[str] = None
    kyc_status: Optional[str] = None

    if user.role == UserRole.MERCHANT:
        stmt = select(Merchant).where(Merchant.user_id == user.id)
        res = await db.execute(stmt)
        merchant = res.scalars().first()
        if merchant:
            merchant_id = merchant.id
            business_name = merchant.business_name
            kyc_status = (
                merchant.kyc_status.value
                if hasattr(merchant.kyc_status, "value")
                else str(merchant.kyc_status)
            )

    shopping_prefs: Optional[list[str]] = None
    if getattr(user, "shopping_preferences", None):
        try:
            val = user.shopping_preferences.strip()
            if val.startswith("["):
                shopping_prefs = json.loads(val)
            else:
                shopping_prefs = [p.strip() for p in val.split(",") if p.strip()]
        except Exception:
            shopping_prefs = []

    # Completeness check:
    # Merchants and Cashiers never undergo Shopper onboarding
    is_shopper = (user.role == UserRole.SHOPPER)
    if not is_shopper:
        onboarding_completed = True
    else:
        has_name = bool(user.full_name and len(user.full_name.strip()) >= 2)
        has_prefs = bool(shopping_prefs and len(shopping_prefs) >= 1)
        has_loc = bool(
            getattr(user, "latitude", None) is not None
            and getattr(user, "longitude", None) is not None
            and bool(getattr(user, "city", None) and getattr(user, "city", "").strip())
            and bool(getattr(user, "address_text", None) and getattr(user, "address_text", "").strip())
        )
        persisted_flag = bool(getattr(user, "onboarding_completed", False))
        onboarding_completed = persisted_flag or (has_name and has_prefs and has_loc)

    return UserOut(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        username=user.username,
        profile_image_url=user.profile_image_url,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        preferred_language=user.preferred_language,
        merchant_id=merchant_id,
        business_name=business_name,
        kyc_status=kyc_status,
        latitude=getattr(user, "latitude", None),
        longitude=getattr(user, "longitude", None),
        city=getattr(user, "city", None),
        address_text=getattr(user, "address_text", None),
        pincode=getattr(user, "pincode", None),
        shopping_preferences=shopping_prefs,
        onboarding_completed=onboarding_completed,
    )
