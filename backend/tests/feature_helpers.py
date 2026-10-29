"""Seeding helpers shared by the client-requirement feature tests."""
import uuid
from dataclasses import dataclass
from typing import Optional

from app.core.security import create_access_token, get_password_hash


def unique_phone() -> str:
    return f"+91{uuid.uuid4().int % 10_000_000_000:010d}"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class SeededStore:
    merchant_id: uuid.UUID
    owner_id: uuid.UUID
    owner_token: str
    staff_id: Optional[uuid.UUID] = None
    staff_token: Optional[str] = None


async def prepare_schema() -> None:
    from app.core.database import Base, engine, ensure_compatibility_schema
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_compatibility_schema()


async def seed_user(role: str = "SHOPPER", full_name: str = "Test Shopper"):
    """Returns (user_id, access_token)."""
    from app.core.database import async_session_factory
    from app.models.user import User, UserRole

    async with async_session_factory() as session:
        user = User(phone=unique_phone(), full_name=full_name, role=UserRole(role), is_active=True)
        session.add(user)
        await session.commit()
        return user.id, create_access_token(subject=str(user.id), role=role)


async def seed_store(*, with_staff: bool = False, can_upload_reels: bool = False,
                     sector: str = "FOOD", latitude: float = 21.1458,
                     longitude: float = 79.0882) -> SeededStore:
    from app.core.database import async_session_factory
    from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector

    owner_id, owner_token = await seed_user("MERCHANT", "Store Owner")
    async with async_session_factory() as session:
        merchant = Merchant(
            user_id=owner_id,
            business_name="Feature Test Store",
            sector=Sector(sector),
            address_text="Sitabuldi, Nagpur",
            city="Nagpur",
            latitude=latitude,
            longitude=longitude,
            kyc_doc_url="https://res.cloudinary.com/fyndo/kyc/doc.pdf",
            kyc_status=KycStatus.APPROVED,
        )
        session.add(merchant)
        await session.flush()
        store = SeededStore(merchant_id=merchant.id, owner_id=owner_id, owner_token=owner_token)
        if with_staff:
            staff = MerchantStaff(
                merchant_id=merchant.id,
                staff_name="Counter Cashier",
                phone=unique_phone(),
                pin_hash=get_password_hash("123456"),
                can_upload_reels=can_upload_reels,
            )
            session.add(staff)
            await session.flush()
            store.staff_id = staff.id
            store.staff_token = create_access_token(
                subject=str(staff.id),
                role="ROLE_CASHIER",
                extra_claims={"merchant_id": str(merchant.id)},
            )
        await session.commit()
        return store


def reel_payload(title: str = "Weekend Special", validity_days: int = 3) -> dict:
    return {
        "title": title,
        "video_url": "https://res.cloudinary.com/fyndo/video/upload/reel.mp4",
        "thumbnail_url": "https://res.cloudinary.com/fyndo/image/upload/reel.webp",
        "duration_seconds": 30,
        "audio_type": "CAMERA_MIC",
        "coupon": {
            "title": "Flat 20% OFF",
            "discount_type": "PERCENTAGE",
            "discount_value": 20,
            "validity_days": validity_days,
        },
    }


async def set_auto_approve(enabled: bool) -> None:
    from app.core.database import async_session_factory
    from app.models.system_settings import AUTO_APPROVE_REELS
    from app.services.settings_service import set_setting

    async with async_session_factory() as session:
        await set_setting(session, AUTO_APPROVE_REELS, enabled)
        await session.commit()


async def set_auto_approve_kyc(enabled: bool) -> None:
    from app.core.database import async_session_factory
    from app.models.system_settings import AUTO_APPROVE_KYC
    from app.services.settings_service import set_setting

    async with async_session_factory() as session:
        await set_setting(session, AUTO_APPROVE_KYC, enabled)
        await session.commit()
