import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.endpoints.auth import get_current_user, get_optional_user
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
import json
from app.models.user import User, UserRole
from app.schemas.common import ResponseEnvelope
from app.services import merchant_engagement_service as engagement
from app.services.category_assets import (
    STORE_CATEGORIES_METADATA,
    normalize_sector,
    get_default_cover_url,
    get_default_logo_url,
)
from app.schemas.merchant import (
    MerchantOnboardRequest,
    MerchantKycResubmissionRequest,
    MerchantProfileUpdateRequest,
    MerchantOut,
    CategoryMetaOut,
    PublicMerchantOut,
    StaffCreateRequest,
    StaffOut,
    StaffUpdateRequest,
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

    from app.services.category_assets import get_default_cover_url, get_default_logo_url

    cover_url = request.cover_url or get_default_cover_url(request.sector)
    logo_url = request.logo_url or get_default_logo_url(request.sector)

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
        kyc_status=KycStatus.PENDING,
        cover_url=cover_url,
        logo_url=logo_url,
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


@router.get("/merchants/categories", response_model=ResponseEnvelope[List[CategoryMetaOut]])
async def get_store_categories():
    """Returns all 20 store primary categories with curated subcategories and icons."""
    data = []
    for cat in STORE_CATEGORIES_METADATA:
        data.append(
            CategoryMetaOut(
                id=cat["id"],
                name=cat["name"],
                icon=cat.get("icon"),
                sub_categories=cat.get("sub_categories", []),
                cover_url=get_default_cover_url(cat["id"]),
                logo_url=get_default_logo_url(cat["id"]),
            )
        )
    return ResponseEnvelope(data=data)


@router.patch("/merchants/profile", response_model=ResponseEnvelope[MerchantOut])
async def update_merchant_profile(
    request: MerchantProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found.")

    dump = request.model_dump(exclude_unset=True)
    if "sector" in dump and dump["sector"]:
        dump["sector"] = normalize_sector(dump["sector"])

    # Cover photo remove or update
    if "cover_url" in dump:
        cov = dump["cover_url"]
        if cov == "" or cov is None:
            merchant.cover_url = None
            merchant.profile_video_thumbnail_url = None
        else:
            merchant.cover_url = cov
            merchant.profile_video_thumbnail_url = cov
        dump.pop("cover_url", None)

    # Logo photo remove or update
    if "logo_url" in dump:
        logo = dump["logo_url"]
        merchant.logo_url = None if (logo == "" or logo is None) else logo
        dump.pop("logo_url", None)

    # Sub-categories JSON serialization
    if "sub_categories" in dump:
        subs = dump["sub_categories"]
        if isinstance(subs, list):
            merchant.sub_categories = json.dumps(subs)
        elif isinstance(subs, str):
            merchant.sub_categories = subs
        else:
            merchant.sub_categories = None
        dump.pop("sub_categories", None)

    for field, value in dump.items():
        if hasattr(merchant, field):
            setattr(merchant, field, value)

    await db.flush()
    await db.refresh(merchant)
    return ResponseEnvelope(data=MerchantOut.model_validate(merchant), message="Store profile updated successfully.")


@router.patch("/merchants/kyc", response_model=ResponseEnvelope[MerchantOut])
async def resubmit_merchant_kyc(
    request: MerchantKycResubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found.")
    if merchant.kyc_status != KycStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only rejected KYC applications can be resubmitted."
        )

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(merchant, field, value)
    merchant.kyc_status = KycStatus.PENDING
    await db.flush()
    await db.refresh(merchant)
    return ResponseEnvelope(data=MerchantOut.model_validate(merchant), message="KYC resubmitted for review.")


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

    # Staff records have an explicit lifecycle; use PATCH to update an existing cashier.
    staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id))
    if staff_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A cashier already exists. Use PATCH /merchants/staff/{id} to update it."
        )

    staff = MerchantStaff(
        merchant_id=merchant.id,
        staff_name=request.staff_name,
        phone=request.phone,
        pin_hash=get_password_hash(request.pin)
    )
    db.add(staff)

    await db.flush()
    await db.refresh(staff)

    return ResponseEnvelope(
        data=StaffOut.model_validate(staff),
        message="Store staff PIN configured successfully"
    )


@router.get("/merchants/staff", response_model=ResponseEnvelope[List[StaffOut]])
async def list_staff(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can view staff.")

    staff_res = await db.execute(
        select(MerchantStaff)
        .where(MerchantStaff.merchant_id == merchant.id)
        .order_by(MerchantStaff.created_at.desc())
    )
    return ResponseEnvelope(data=[StaffOut.model_validate(staff) for staff in staff_res.scalars().all()])


@router.patch("/merchants/staff/{staff_id}", response_model=ResponseEnvelope[StaffOut])
async def update_staff(
    staff_id: uuid.UUID,
    request: StaffUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    merchant_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    merchant = merchant_res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only merchants can update staff.")

    staff_res = await db.execute(
        select(MerchantStaff).where(
            MerchantStaff.id == staff_id,
            MerchantStaff.merchant_id == merchant.id,
        )
    )
    staff = staff_res.scalars().first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")

    values = request.model_dump(exclude_unset=True)
    if "pin" in values:
        staff.pin_hash = get_password_hash(values.pop("pin"))
    for field, value in values.items():
        setattr(staff, field, value)
    await db.flush()
    await db.refresh(staff)
    return ResponseEnvelope(data=StaffOut.model_validate(staff), message="Staff member updated successfully.")


@router.get("/merchants/{merchant_id}", response_model=ResponseEnvelope[PublicMerchantOut])
async def get_public_merchant(
    merchant_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Merchant).where(
            Merchant.id == merchant_id,
            Merchant.kyc_status == KycStatus.APPROVED,
        )
    )
    merchant = res.scalars().first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant storefront not found.")

    ratings = await engagement.rating_summary(db, merchant.id)
    return ResponseEnvelope(
        data=PublicMerchantOut(
            id=merchant.id,
            business_name=merchant.business_name,
            sector=merchant.sector.value if hasattr(merchant.sector, "value") else str(merchant.sector),
            address_text=merchant.address_text,
            city=merchant.city,
            latitude=merchant.latitude,
            longitude=merchant.longitude,
            profile_video_url=merchant.profile_video_url,
            profile_video_thumbnail_url=merchant.profile_video_thumbnail_url,
            followers_count=await engagement.followers_count(db, merchant.id),
            is_following=await engagement.is_following(db, merchant.id, current_user),
            rating_average=ratings["average"],
            rating_count=ratings["count"],
        )
    )
