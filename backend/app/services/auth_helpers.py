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

    return UserOut(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        preferred_language=user.preferred_language,
        merchant_id=merchant_id,
        business_name=business_name,
        kyc_status=kyc_status
    )
