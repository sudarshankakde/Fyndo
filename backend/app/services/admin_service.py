import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.security import get_password_hash
from app.models.coupon import CouponTemplate, DiscountType, RedemptionsLedger
from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminMerchantCreateRequest,
    AdminMerchantDetail,
    AdminMerchantUpdateRequest,
    AdminReelCreateRequest,
    AdminReelListItem,
    AdminReelUpdateRequest,
    AdminStaffUpdateRequest,
    AdminStatsResponse,
)
from app.services.cloudinary_service import CloudinaryService
from app.services.reel_lifecycle_service import start_offer_clock


class AdminService:
    @classmethod
    async def get_platform_stats(cls, db: AsyncSession) -> AdminStatsResponse:
        total_merchants = (await db.execute(select(func.count(Merchant.id)))).scalar() or 0
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        total_reels = (await db.execute(select(func.count(Reel.id)).where(Reel.deleted_at.is_(None)))).scalar() or 0
        total_redemptions = (await db.execute(select(func.count(RedemptionsLedger.id)))).scalar() or 0
        total_discount = (await db.execute(select(func.sum(RedemptionsLedger.discount_applied)))).scalar() or 0.0
        pending_moderation = (await db.execute(
            select(func.count(Reel.id)).where(Reel.status == ReelStatus.PENDING_MODERATION, Reel.deleted_at.is_(None))
        )).scalar() or 0

        return AdminStatsResponse(
            total_merchants=total_merchants,
            total_users=total_users,
            total_reels=total_reels,
            total_redemptions=total_redemptions,
            total_discount_applied=float(total_discount),
            pending_moderation_count=pending_moderation
        )

    @classmethod
    async def list_merchants(cls, db: AsyncSession) -> List[AdminMerchantDetail]:
        stmt = (
            select(Merchant)
            .options(
                selectinload(Merchant.owner),
                selectinload(Merchant.staff),
                selectinload(Merchant.reels)
            )
            .order_by(Merchant.created_at.desc())
        )
        merchants = (await db.execute(stmt)).scalars().all()
        result = []
        for m in merchants:
            def val(v): return v.value if hasattr(v, "value") else str(v)
            active_reels = [r for r in m.reels if r.deleted_at is None]
            result.append(
                AdminMerchantDetail(
                    id=m.id,
                    business_name=m.business_name,
                    sector=val(m.sector),
                    address_text=m.address_text,
                    city=m.city,
                    latitude=m.latitude,
                    longitude=m.longitude,
                    owner_phone=m.owner.phone if m.owner else "+910000000000",
                    kyc_status=val(m.kyc_status),
                    staff_name=m.staff[0].staff_name if m.staff else None,
                    staff_phone=m.staff[0].phone if m.staff else None,
                    reels_count=len(active_reels),
                    created_at=m.created_at
                )
            )
        return result

    @classmethod
    async def create_merchant(cls, req: AdminMerchantCreateRequest, db: AsyncSession) -> AdminMerchantDetail:
        # Check or create owner user
        phone = req.owner_phone.strip().replace(" ", "")
        user_res = await db.execute(select(User).where(User.phone == phone))
        owner = user_res.scalars().first()
        if not owner:
            owner = User(phone=phone, full_name=f"{req.business_name} Owner", role=UserRole.MERCHANT)
            db.add(owner)
            await db.flush()

        merchant = Merchant(
            user_id=owner.id,
            business_name=req.business_name,
            sector=Sector(req.sector.upper()),
            address_text=req.address_text,
            city=req.city,
            latitude=req.latitude,
            longitude=req.longitude,
            gstin=req.gstin,
            kyc_doc_url="https://res.cloudinary.com/fyndo/kyc/verified_sample.jpg",
            kyc_status=KycStatus.APPROVED
        )
        db.add(merchant)
        await db.flush()

        if req.staff_pin:
            staff = MerchantStaff(
                merchant_id=merchant.id,
                staff_name=req.staff_name or "Store Cashier",
                phone=phone,
                pin_hash=get_password_hash(req.staff_pin),
                is_active=True
            )
            db.add(staff)
            await db.flush()

        return (await cls.list_merchants(db))[0]

    @classmethod
    async def update_merchant(cls, merchant_id: uuid.UUID, req: AdminMerchantUpdateRequest, db: AsyncSession) -> Optional[Merchant]:
        res = await db.execute(select(Merchant).where(Merchant.id == merchant_id))
        m = res.scalars().first()
        if not m:
            return None
        if req.business_name: m.business_name = req.business_name
        if req.sector: m.sector = Sector(req.sector.upper())
        if req.address_text: m.address_text = req.address_text
        if req.city: m.city = req.city
        if req.latitude is not None: m.latitude = req.latitude
        if req.longitude is not None: m.longitude = req.longitude
        if req.gstin is not None: m.gstin = req.gstin
        if req.kyc_status: m.kyc_status = KycStatus(req.kyc_status.upper())
        await db.flush()
        return m

    @classmethod
    async def list_all_reels(cls, status: Optional[str], db: AsyncSession) -> List[AdminReelListItem]:
        stmt = (
            select(Reel)
            .options(selectinload(Reel.merchant), selectinload(Reel.coupon_template))
            .where(Reel.deleted_at.is_(None))
            .order_by(Reel.created_at.desc())
        )
        if status and status.upper() != "ALL":
            stmt = stmt.where(Reel.status == ReelStatus(status.upper()))

        reels = (await db.execute(stmt)).scalars().all()
        items = []
        for r in reels:
            def val(v): return v.value if hasattr(v, "value") else str(v) if v is not None else None
            m = r.merchant
            ct = r.coupon_template
            items.append(
                AdminReelListItem(
                    id=r.id,
                    title=r.title,
                    video_url=r.video_url,
                    thumbnail_url=r.thumbnail_url,
                    duration_seconds=r.duration_seconds,
                    audio_type=val(r.audio_type) or "CAMERA_MIC",
                    status=val(r.status),
                    merchant_id=m.id if m else uuid.uuid4(),
                    merchant_name=m.business_name if m else "Unknown",
                    sector=val(m.sector) if m else "GENERAL",
                    city=m.city if m else "Nagpur",
                    coupon_title=ct.title if ct else None,
                    discount_type=val(ct.discount_type) if ct else None,
                    discount_value=float(ct.discount_value) if ct else None,
                    min_order_amount=float(ct.min_order_amount) if ct else None,
                    validity_days=ct.validity_days if ct else None
                )
            )
        return items

    @classmethod
    async def create_reel(cls, req: AdminReelCreateRequest, db: AsyncSession) -> uuid.UUID:
        v_url = CloudinaryService.get_optimized_video_url(req.video_url) or req.video_url
        hls_url = CloudinaryService.get_hls_url(video_url=req.video_url)
        reel = Reel(
            merchant_id=req.merchant_id,
            title=req.title,
            duration_seconds=req.duration_seconds,
            video_url=v_url,
            video_hls_url=hls_url,
            thumbnail_url=req.thumbnail_url,
            audio_type=AudioType.CAMERA_MIC,
            status=ReelStatus.APPROVED
        )
        db.add(reel)
        await db.flush()

        coupon = CouponTemplate(
            merchant_id=req.merchant_id,
            reel_id=reel.id,
            title=req.coupon_title,
            discount_type=DiscountType(req.discount_type.upper()),
            discount_value=req.discount_value,
            validity_days=req.validity_days,
            min_order_amount=req.min_order_amount,
            is_active=True
        )
        db.add(coupon)
        start_offer_clock(reel, coupon)
        await db.flush()
        return reel.id

    @classmethod
    async def update_staff_pin(cls, merchant_id: uuid.UUID, req: AdminStaffUpdateRequest, db: AsyncSession) -> MerchantStaff:
        res = await db.execute(select(MerchantStaff).where(MerchantStaff.merchant_id == merchant_id))
        staff = res.scalars().first()
        pin_hash = get_password_hash(req.pin)
        if staff:
            staff.staff_name = req.staff_name
            staff.phone = req.phone
            staff.pin_hash = pin_hash
            staff.is_active = True
        else:
            staff = MerchantStaff(
                merchant_id=merchant_id,
                staff_name=req.staff_name,
                phone=req.phone,
                pin_hash=pin_hash,
                is_active=True
            )
            db.add(staff)
        await db.flush()
        return staff
