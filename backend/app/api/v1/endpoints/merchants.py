from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
from app.models.user import User, UserRole
from app.schemas.common import ResponseEnvelope
from app.schemas.merchant import (
    MerchantOnboardRequest,
    MerchantOut,
    StaffCreateRequest,
    StaffOut,
)

router = APIRouter()


@router.post("/merchants/onboard", response_model=ResponseEnvelope[MerchantOut])
async def onboard_merchant(
    request: MerchantOnboardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers a new merchant profile and queues KYC documents for Admin verification."""
    # Check if user already owns a merchant
    existing_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    if existing_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already registered a merchant store."
        )

    merchant = Merchant(
        user_id=current_user.id,
        business_name=request.business_name,
        sector=Sector(request.sector),
        address_text=request.address_text,
        city=request.city,
        latitude=request.latitude,
        longitude=request.longitude,
        gstin=request.gstin,
        kyc_doc_url=request.kyc_doc_url,
        kyc_status=KycStatus.PENDING
    )
    db.add(merchant)

    # Upgrade user role to MERCHANT
    current_user.role = UserRole.MERCHANT

    await db.flush()
    await db.refresh(merchant)

    return ResponseEnvelope(
        data=MerchantOut.model_validate(merchant),
        message="Merchant onboarding submitted. Pending admin review."
    )


@router.get("/merchants/profile", response_model=ResponseEnvelope[MerchantOut])
async def get_merchant_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves current user's merchant profile."""
    res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found.")

    return ResponseEnvelope(data=MerchantOut.model_validate(merchant))


@router.post("/merchants/staff", response_model=ResponseEnvelope[StaffOut])
async def create_staff(
    request: StaffCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Configures the single designated cashier/staff scanner account for the store."""
    res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can configure staff.")

    # Check if staff already exists (enforcing strictly max 1 staff per merchant in Beta)
    staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id))
    staff = staff_res.scalars().first()

    pin_hash = get_password_hash(request.pin)

    if staff:
        # Update existing staff credentials
        staff.staff_name = request.staff_name
        staff.phone = request.phone
        staff.pin_hash = pin_hash
        staff.is_active = True
    else:
        staff = MerchantStaff(
            merchant_id=merchant.id,
            staff_name=request.staff_name,
            phone=request.phone,
            pin_hash=pin_hash
        )
        db.add(staff)

    await db.flush()
    await db.refresh(staff)

    return ResponseEnvelope(
        data=StaffOut.model_validate(staff),
        message="Store staff PIN configured successfully"
    )
