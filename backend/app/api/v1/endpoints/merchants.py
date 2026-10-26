import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.geo import calculate_haversine_distance
from app.api.v1.endpoints.auth import get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.merchant import KycStatus, Merchant, MerchantOnboardingDraft, MerchantStaff, Sector
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
    MerchantDraftSaveRequest,
    MerchantDraftOut,
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


@router.get("/merchants/onboard/draft", response_model=ResponseEnvelope[MerchantDraftOut])
async def get_onboarding_draft(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves current user's saved merchant onboarding draft."""
    res = await db.execute(select(MerchantOnboardingDraft).where(MerchantOnboardingDraft.user_id == current_user.id))
    draft = res.scalars().first()
    if not draft:
        return ResponseEnvelope(
            data=MerchantDraftOut(has_draft=False, step=1),
            message="No active draft found."
        )

    return ResponseEnvelope(
        data=MerchantDraftOut(
            has_draft=True,
            step=draft.step,
            business_name=draft.business_name,
            sector=draft.sector,
            description=draft.description,
            address_text=draft.address_text,
            city=draft.city,
            pincode=draft.pincode,
            latitude=draft.latitude,
            longitude=draft.longitude,
            gstin=draft.gstin,
            kyc_doc_url=draft.kyc_doc_url,
            updated_at=draft.updated_at,
        ),
        message="Draft retrieved successfully."
    )


@router.put("/merchants/onboard/draft", response_model=ResponseEnvelope[MerchantDraftOut])
async def save_onboarding_draft(
    request: MerchantDraftSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upserts current user's merchant onboarding draft."""
    res = await db.execute(select(MerchantOnboardingDraft).where(MerchantOnboardingDraft.user_id == current_user.id))
    draft = res.scalars().first()
    if not draft:
        draft = MerchantOnboardingDraft(
            user_id=current_user.id,
            step=request.step,
            business_name=request.business_name,
            sector=request.sector,
            description=request.description,
            address_text=request.address_text,
            city=request.city,
            pincode=request.pincode,
            latitude=request.latitude,
            longitude=request.longitude,
            gstin=request.gstin,
            kyc_doc_url=request.kyc_doc_url,
        )
        db.add(draft)
    else:
        draft.step = request.step
        if request.business_name is not None:
            draft.business_name = request.business_name
        if request.sector is not None:
            draft.sector = request.sector
        if request.description is not None:
            draft.description = request.description
        if request.address_text is not None:
            draft.address_text = request.address_text
        if request.city is not None:
            draft.city = request.city
        if request.pincode is not None:
            draft.pincode = request.pincode
        if request.latitude is not None:
            draft.latitude = request.latitude
        if request.longitude is not None:
            draft.longitude = request.longitude
        if request.gstin is not None:
            draft.gstin = request.gstin
        if request.kyc_doc_url is not None:
            draft.kyc_doc_url = request.kyc_doc_url

    await db.flush()
    await db.refresh(draft)

    return ResponseEnvelope(
        data=MerchantDraftOut(
            has_draft=True,
            step=draft.step,
            business_name=draft.business_name,
            sector=draft.sector,
            description=draft.description,
            address_text=draft.address_text,
            city=draft.city,
            pincode=draft.pincode,
            latitude=draft.latitude,
            longitude=draft.longitude,
            gstin=draft.gstin,
            kyc_doc_url=draft.kyc_doc_url,
            updated_at=draft.updated_at,
        ),
        message="Draft saved successfully."
    )


@router.delete("/merchants/onboard/draft", response_model=ResponseEnvelope[bool])
async def delete_onboarding_draft(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes current user's merchant onboarding draft."""
    await db.execute(delete(MerchantOnboardingDraft).where(MerchantOnboardingDraft.user_id == current_user.id))
    await db.flush()
    return ResponseEnvelope(data=True, message="Draft cleared successfully.")


@router.post("/merchants/onboard", response_model=ResponseEnvelope[MerchantOut])
async def onboard_merchant(
    request: MerchantOnboardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers a new merchant profile and queues KYC documents for Admin verification."""
    # Check if user already owns a merchant (idempotency check)
    existing_res = await db.execute(select(Merchant).where(Merchant.user_id == current_user.id))
    existing_merchant = existing_res.scalars().first()
    if existing_merchant:
        # User already registered a merchant; ensure user role is updated and return existing merchant idempotently
        if current_user.role != UserRole.MERCHANT:
            current_user.role = UserRole.MERCHANT
            await db.flush()
        # Clean up any lingering draft
        await db.execute(delete(MerchantOnboardingDraft).where(MerchantOnboardingDraft.user_id == current_user.id))
        await db.flush()
        return ResponseEnvelope(
            data=MerchantOut.model_validate(existing_merchant),
            message="Merchant profile already exists."
        )

    # Normalize sector
    normalized_sector_str = normalize_sector(request.sector)
    try:
        sector_enum = Sector(normalized_sector_str)
    except ValueError:
        sector_enum = Sector.OTHER

    cover_url = request.cover_url or get_default_cover_url(sector_enum.value)
    logo_url = request.logo_url or get_default_logo_url(sector_enum.value)

    merchant = Merchant(
        user_id=current_user.id,
        business_name=request.business_name,
        sector=sector_enum,
        address_text=request.address_text,
        city=request.city,
        latitude=request.latitude,
        longitude=request.longitude,
        gstin=request.gstin,
        kyc_doc_url=request.kyc_doc_url,
        kyc_status=KycStatus.PENDING,
        cover_url=cover_url,
        logo_url=logo_url,
        description=request.description,
    )
    db.add(merchant)

    # Upgrade user role to MERCHANT only upon successful creation
    current_user.role = UserRole.MERCHANT

    # Clean up any saved onboarding draft atomically
    await db.execute(delete(MerchantOnboardingDraft).where(MerchantOnboardingDraft.user_id == current_user.id))

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


KNOWN_CITY_CENTERS = {
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "mumbai": (19.0760, 72.8777),
    "nashik": (19.9975, 73.7898),
    "bengaluru": (12.9716, 77.5946),
    "delhi": (28.6139, 77.2090),
    "galleborgaon": (20.0889, 75.1195),
    "chhatrapati sambhajinagar": (19.8762, 75.3433),
    "aurangabad": (19.8762, 75.3433),
}


@router.get("/merchants/cities", response_model=ResponseEnvelope[List[dict]])
async def list_active_cities(
    db: AsyncSession = Depends(get_db),
):
    """Returns unique eligible cities and their active shop counts directly via SQL from the merchants table, sorted ascending by count then city name."""
    norm_city = func.trim(func.lower(Merchant.city))
    query = (
        select(
            norm_city.label("canonical_city"),
            func.count(func.distinct(Merchant.id)).label("shop_count"),
            func.avg(Merchant.latitude).label("latitude"),
            func.avg(Merchant.longitude).label("longitude"),
        )
        .join(User, Merchant.user_id == User.id)
        .where(
            User.is_active == True,
            Merchant.city.isnot(None),
            func.length(func.trim(Merchant.city)) > 0,
        )
    )
    if settings.ENVIRONMENT != "development":
        query = query.where(Merchant.kyc_status == KycStatus.APPROVED)
    else:
        query = query.where(Merchant.kyc_status != KycStatus.REJECTED)

    query = query.group_by(norm_city).order_by(desc("shop_count"), asc("canonical_city"))
    res = await db.execute(query)
    rows = res.all()

    cities = []
    for row in rows:
        if not row.canonical_city or row.shop_count <= 0:
            continue
        c_lower = row.canonical_city.lower()
        if c_lower in KNOWN_CITY_CENTERS:
            c_lat, c_lon = KNOWN_CITY_CENTERS[c_lower]
        else:
            c_lat = float(row.latitude) if row.latitude is not None else None
            c_lon = float(row.longitude) if row.longitude is not None else None
        cities.append({
            "city": row.canonical_city.title(),
            "shop_count": int(row.shop_count),
            "latitude": c_lat,
            "longitude": c_lon,
        })

    return ResponseEnvelope(
        data=cities,
        message=f"Found {len(cities)} serviceable cities." if cities else "No active cities found."
    )


@router.get("/merchants", response_model=ResponseEnvelope[List[dict]])
async def list_merchants(
    city: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: int = Query(50),
    sector: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Fetches verified storefronts for a given city and/or proximity coordinates."""
    query = (
        select(Merchant)
        .join(User, Merchant.user_id == User.id)
        .where(
            User.is_active == True,
            Merchant.business_name.isnot(None),
            func.length(func.trim(Merchant.business_name)) > 0,
        )
    )
    if settings.ENVIRONMENT != "development":
        query = query.where(Merchant.kyc_status == KycStatus.APPROVED)
    else:
        query = query.where(Merchant.kyc_status != KycStatus.REJECTED)

    if city and city.strip():
        query = query.where(func.lower(func.trim(Merchant.city)) == city.strip().lower())

    if sector and sector.strip() and sector.strip().lower() != "all":
        query = query.where(Merchant.sector == sector.strip().upper())

    query = query.order_by(Merchant.created_at.desc())
    res = await db.execute(query)
    merchants = res.scalars().all()

    shops = []
    for m in merchants:
        dist_m = 0
        if lat is not None and lon is not None and m.latitude is not None and m.longitude is not None:
            dist_m = int(calculate_haversine_distance(lat, lon, m.latitude, m.longitude))
            if not city and dist_m > (radius_km * 1000):
                continue

        m_sector = getattr(m.sector, "value", str(m.sector))
        shops.append({
            "id": str(m.id),
            "name": m.business_name,
            "category": m_sector,
            "locality": m.address_text.split(",")[0].strip() if m.address_text else (m.city or "Local"),
            "city": m.city,
            "address": m.address_text,
            "latitude": m.latitude,
            "longitude": m.longitude,
            "distance_meters": dist_m,
            "image": m.cover_url or get_default_cover_url(m_sector),
            "logo": m.logo_url or get_default_logo_url(m_sector),
            "description": m.description or f"Verified {m_sector} store in {m.city or 'your city'}",
            "active_deal": "Instant Cashier Pass",
            "is_verified": True,
        })

    if lat is not None and lon is not None:
        shops.sort(key=lambda s: s["distance_meters"])

    return ResponseEnvelope(
        data=shops,
        message=f"Found {len(shops)} shops." if shops else "No shops found."
    )


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
            cover_url=merchant.cover_url,
            logo_url=merchant.logo_url,
            followers_count=await engagement.followers_count(db, merchant.id),
            is_following=await engagement.is_following(db, merchant.id, current_user),
            rating_average=ratings["average"],
            rating_count=ratings["count"],
        )
    )
