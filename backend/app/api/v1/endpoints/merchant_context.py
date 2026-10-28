import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.endpoints.auth import AuthContext, get_auth_context
from app.core.context import set_user_id
from app.core.database import get_db
from app.models.merchant import Merchant, MerchantStaff
from app.models.user import User


class MerchantContext:
    def __init__(
        self,
        merchant: Merchant,
        is_staff: bool,
        staff: Optional[MerchantStaff] = None,
        user: Optional[User] = None,
        can_upload_reels: bool = True,
        can_manage_content: bool = True,
    ):
        self.merchant = merchant
        self.is_staff = is_staff
        self.staff = staff
        self.user = user
        self.can_upload_reels = can_upload_reels
        self.can_manage_content = can_manage_content

    @property
    def merchant_id(self) -> uuid.UUID:
        return self.merchant.id

    @property
    def staff_id(self) -> Optional[uuid.UUID]:
        return self.staff.id if self.staff else None


async def get_merchant_context(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db)
) -> MerchantContext:
    """Resolves merchant store context for either a store owner or authorized counter staff."""
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

        staff = await db.get(MerchantStaff, auth.subject_id)
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
        merchant = await db.get(Merchant, staff.merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store associated with this terminal was not found."
            )
        can_upload = bool(staff.can_upload_reels or getattr(staff, "can_manage_content", False))
        can_manage = bool(getattr(staff, "can_manage_content", False))
        return MerchantContext(
            merchant=merchant,
            is_staff=True,
            staff=staff,
            user=None,
            can_upload_reels=can_upload,
            can_manage_content=can_manage,
        )

    result = await db.execute(select(User).where(User.id == auth.subject_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or suspended."
        )
    merch_res = await db.execute(select(Merchant).where(Merchant.user_id == user.id))
    merchant = merch_res.scalars().first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only registered merchants can access this store resource."
        )
    set_user_id(user.id)
    return MerchantContext(
        merchant=merchant,
        is_staff=False,
        staff=None,
        user=user,
        can_upload_reels=True,
        can_manage_content=True,
    )
