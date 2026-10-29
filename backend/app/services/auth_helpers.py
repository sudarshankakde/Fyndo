import json
import uuid
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.coupon import RedemptionsLedger, UserCoupon
from app.models.merchant import Merchant
from app.models.user import User, UserRole
from app.schemas.auth import ShopperProfileMetrics, UserOut


async def build_user_out(user: User, db: AsyncSession) -> UserOut:
    """Helper to convert User model into UserOut schema with merchant details."""
    merchant_id: Optional[uuid.UUID] = None
    business_name: Optional[str] = None
    kyc_status: Optional[str] = None

    merchant = None
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
    is_shopper = (user.role == UserRole.SHOPPER)
    if user.role == UserRole.MERCHANT:
        has_store = bool(
            merchant is not None
            and merchant.business_name
            and len(merchant.business_name.strip()) >= 2
        )
        onboarding_completed = has_store or bool(getattr(user, "onboarding_completed", False))
    elif user.role == UserRole.SUPER_ADMIN:
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

    metrics: Optional[ShopperProfileMetrics] = None
    if is_shopper:
        # Calculate real Shopper metrics via SQL aggregations
        total_saved_stmt = (
            select(func.coalesce(func.sum(RedemptionsLedger.discount_applied), 0.0))
            .join(UserCoupon, RedemptionsLedger.user_coupon_id == UserCoupon.id)
            .where(UserCoupon.user_id == user.id)
        )
        total_saved_res = await db.execute(total_saved_stmt)
        total_saved = float(total_saved_res.scalar() or 0.0)

        claims_stmt = (
            select(func.count(UserCoupon.id))
            .where(UserCoupon.user_id == user.id)
        )
        claims_res = await db.execute(claims_stmt)
        offers_claimed = int(claims_res.scalar() or 0)

        stores_stmt = (
            select(func.count(func.distinct(RedemptionsLedger.merchant_id)))
            .join(UserCoupon, RedemptionsLedger.user_coupon_id == UserCoupon.id)
            .where(UserCoupon.user_id == user.id)
        )
        stores_res = await db.execute(stores_stmt)
        stores_visited = int(stores_res.scalar() or 0)

        metrics = ShopperProfileMetrics(
            total_saved=total_saved,
            offers_claimed=offers_claimed,
            stores_visited=stores_visited,
        )

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
        created_at=getattr(user, "created_at", None),
        metrics=metrics,
    )
