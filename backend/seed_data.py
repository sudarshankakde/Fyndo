#!/usr/bin/env python3
"""
Fyndo Demo Seed Script
======================
Creates production-like dummy data so the mobile app renders real backend data.

What it seeds
─────────────
  • 6 Merchant users  (phone 91900000001x, OTP-less via direct DB insert)
  • 6 Merchant profiles  (APPROVED KYC, spread across Nagpur localities)
  • 18 Reels  (3 per merchant, APPROVED status, real Cloudinary thumbnails)
  • 18 CouponTemplates  (one per reel, mix of PERCENTAGE / FLAT_AMOUNT / BOGO)
  • 3 Shopper users  (phone 91800000001x)
  • 6 UserCoupons  (shoppers with some claimed + some redeemed)
  • 3 RedemptionsLedger rows
  • MerchantStaff  (one per merchant for cashier login)

Usage
─────
  # from d:/IAOS/Fyndo/Fyndo (repo root)
  cd backend
  .venv\\Scripts\\activate
  pip install -r requirements.txt
  cd ..                        # back to repo root
  python backend/seed_data.py

Idempotent
──────────
Re-running the script is safe — it checks for existing phone numbers and
skips rows that already exist.
"""

import asyncio
import os
import sys
import uuid
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# ── Make the backend package importable ──────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── Load env ─────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

# ── SQLAlchemy ────────────────────────────────────────────────────────────────
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://fyndo_user:fyndo_secure_password@localhost:5432/fyndo_db",
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# ── Model imports ─────────────────────────────────────────────────────────────
from app.models.user import User, UserRole
from app.models.merchant import Merchant, MerchantStaff, Sector, KycStatus
from app.models.reel import Reel, ReelStatus, AudioType
from app.models.coupon import CouponTemplate, UserCoupon, RedemptionsLedger, DiscountType, CouponStatus

# ── Media URLs ────────────────────────────────────────────────────────────────
THUMBNAILS = {
    "cafe": [
        "https://images.unsplash.com/photo-1511920170033-f8396924c348?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1521302200778-33500795e128?w=800&auto=format&fit=crop",
    ],
    "fashion": [
        "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1445205170230-053b83016050?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&auto=format&fit=crop",
    ],
    "footwear": [
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=800&auto=format&fit=crop",
    ],
    "electronics": [
        "https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=800&auto=format&fit=crop",
    ],
    "food": [
        "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&auto=format&fit=crop",
    ],
    "salon": [
        "https://images.unsplash.com/photo-1560066984-138daaa70c17?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1582095133179-bfd08e2fb6b8?w=800&auto=format&fit=crop",
    ],
}

PLACEHOLDER_VIDEO = "https://www.w3schools.com/html/mov_bbb.mp4"

# ── Merchant seed data ────────────────────────────────────────────────────────
MERCHANTS_SEED = [
    {
        "phone": "919000000011",
        "full_name": "Rajesh Agrawal",
        "business_name": "The Brew House",
        "sector": Sector.FOOD,
        "address_text": "Plot 12, Dharampeth Extension, Nagpur 440010",
        "city": "Nagpur",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "thumb_key": "cafe",
        "reels": [
            {"title": "Artisanal Latte & Pour Over Experience", "caption": "Wake up to award-winning coffee"},
            {"title": "Cold Brew Collection Summer Special", "caption": "Chilled vibes, bold flavour"},
            {"title": "Weekend Brunch Bites at The Brew House", "caption": "Egg benedicts & more"},
        ],
        "coupons": [
            {"title": "Flat 20% Off on All Coffees", "type": DiscountType.PERCENTAGE, "value": 20, "min": 100, "days": 30, "terms": "Valid on all beverages. One per customer per day."},
            {"title": "Rs 50 Off on Cold Brew Combos", "type": DiscountType.FLAT_AMOUNT, "value": 50, "min": 200, "days": 21, "terms": "Valid on cold brew + snack combos only."},
            {"title": "Buy 1 Get 1 on Brunch Platters", "type": DiscountType.BOGO, "value": 1, "min": 300, "days": 14, "terms": "Weekend brunch menu only. Dine-in exclusive."},
        ],
    },
    {
        "phone": "919000000012",
        "full_name": "Priya Sharma",
        "business_name": "Silk Route Boutique",
        "sector": Sector.FASHION,
        "address_text": "Shop 4, Sitabuldi Main Road, Nagpur 440012",
        "city": "Nagpur",
        "latitude": 21.1502,
        "longitude": 79.0862,
        "thumb_key": "fashion",
        "reels": [
            {"title": "Festive Saree Collection 2026", "caption": "Dazzle this season"},
            {"title": "Indo-Western Fusion New Arrivals", "caption": "Where tradition meets trend"},
            {"title": "Kurti and Co-ord Set Sale", "caption": "Up to 40% off limited pieces"},
        ],
        "coupons": [
            {"title": "30% Off on Silk Sarees", "type": DiscountType.PERCENTAGE, "value": 30, "min": 1500, "days": 25, "terms": "Applicable on silk and cotton-silk sarees only."},
            {"title": "Rs 200 Off on Indo-Western Sets", "type": DiscountType.FLAT_AMOUNT, "value": 200, "min": 999, "days": 20, "terms": "Min purchase Rs999. Cannot be clubbed with other offers."},
            {"title": "Buy 2 Kurtis Get 1 Free", "type": DiscountType.BOGO, "value": 1, "min": 800, "days": 15, "terms": "Lowest priced kurti free. All sizes included."},
        ],
    },
    {
        "phone": "919000000013",
        "full_name": "Amit Patel",
        "business_name": "Sole Republic",
        "sector": Sector.FOOTWEAR,
        "address_text": "Ground Floor, Empress Mall, Nagpur 440018",
        "city": "Nagpur",
        "latitude": 21.1425,
        "longitude": 79.0956,
        "thumb_key": "footwear",
        "reels": [
            {"title": "Nike and Adidas Monsoon Sale", "caption": "Step up your game"},
            {"title": "Formal Leather Collection Office Essentials", "caption": "Look sharp, feel sharp"},
            {"title": "Campus Footwear Back to College Deals", "caption": "Budget friendly picks"},
        ],
        "coupons": [
            {"title": "Flat 25% Off on Sports Shoes", "type": DiscountType.PERCENTAGE, "value": 25, "min": 800, "days": 30, "terms": "Applicable on Nike, Adidas, Puma brands."},
            {"title": "Rs 300 Off on Formal Footwear", "type": DiscountType.FLAT_AMOUNT, "value": 300, "min": 1500, "days": 18, "terms": "Valid on leather formals only."},
            {"title": "Buy 1 Pair Get 1 at 50% Off", "type": DiscountType.BOGO, "value": 1, "min": 1200, "days": 12, "terms": "Applies to equal or lower priced pair."},
        ],
    },
    {
        "phone": "919000000014",
        "full_name": "Sunita Mehta",
        "business_name": "Gadget Galaxy",
        "sector": Sector.ELECTRONICS,
        "address_text": "Shop 22, LIC Square, Nagpur 440001",
        "city": "Nagpur",
        "latitude": 21.1484,
        "longitude": 79.0831,
        "thumb_key": "electronics",
        "reels": [
            {"title": "Top 5 Budget Earbuds Under 1000", "caption": "Bass meets budget"},
            {"title": "Laptop Accessories Haul WFH Edition", "caption": "Work smarter not harder"},
            {"title": "Smart Watch Deals Festive Season", "caption": "Track fitness, score deals"},
        ],
        "coupons": [
            {"title": "15% Off on Earbuds and Headphones", "type": DiscountType.PERCENTAGE, "value": 15, "min": 500, "days": 28, "terms": "Brand: boAt, JBL, Noise. Excludes ANC models."},
            {"title": "Rs 500 Off on Laptop Accessories", "type": DiscountType.FLAT_AMOUNT, "value": 500, "min": 2000, "days": 21, "terms": "On keyboard, mouse, or hub combos."},
            {"title": "Smart Watch Flat 20% Off", "type": DiscountType.PERCENTAGE, "value": 20, "min": 2500, "days": 14, "terms": "Valid on Noise and Fire-Boltt models."},
        ],
    },
    {
        "phone": "919000000015",
        "full_name": "Vikram Deshmukh",
        "business_name": "Chai Pe Charcha",
        "sector": Sector.FOOD,
        "address_text": "Near Variety Square, Itwari, Nagpur 440002",
        "city": "Nagpur",
        "latitude": 21.1520,
        "longitude": 79.0790,
        "thumb_key": "food",
        "reels": [
            {"title": "Nagpuri Masala Chai Our Story", "caption": "Straight from the heart of Nagpur"},
            {"title": "Poha and Chai Combo Breakfast Special", "caption": "The real Nagpur breakfast"},
            {"title": "Evening Snack Menu Samosa and Kachori", "caption": "Your 5pm craving sorted"},
        ],
        "coupons": [
            {"title": "Rs 30 Off on Chai Combo", "type": DiscountType.FLAT_AMOUNT, "value": 30, "min": 80, "days": 14, "terms": "Valid on chai + snack combos. Dine-in only."},
            {"title": "Buy 2 Teas Get 1 Free", "type": DiscountType.BOGO, "value": 1, "min": 60, "days": 10, "terms": "Any tea variety. Takeaway included."},
            {"title": "20% Off on Breakfast Thali", "type": DiscountType.PERCENTAGE, "value": 20, "min": 100, "days": 20, "terms": "Weekdays before 11am only."},
        ],
    },
    {
        "phone": "919000000016",
        "full_name": "Neha Kulkarni",
        "business_name": "Glow and Glam Salon",
        "sector": Sector.FASHION,
        "address_text": "First Floor, Ramdaspeth Chowk, Nagpur 440010",
        "city": "Nagpur",
        "latitude": 21.1469,
        "longitude": 79.0915,
        "thumb_key": "salon",
        "reels": [
            {"title": "Bridal Makeup Package 2026 Weddings", "caption": "Your dream look, our expertise"},
            {"title": "Keratin Treatment Monsoon Hair Care", "caption": "Frizz-free all season"},
            {"title": "Manicure and Pedicure Combo Deals", "caption": "Pamper yourself this weekend"},
        ],
        "coupons": [
            {"title": "25% Off on Bridal Makeup Package", "type": DiscountType.PERCENTAGE, "value": 25, "min": 3000, "days": 45, "terms": "Book 2 weeks in advance. Non-refundable."},
            {"title": "Rs 200 Off on Keratin Treatment", "type": DiscountType.FLAT_AMOUNT, "value": 200, "min": 1500, "days": 30, "terms": "Valid for hair up to shoulder length."},
            {"title": "Mani-Pedi Combo Get 1 Service Free", "type": DiscountType.BOGO, "value": 1, "min": 500, "days": 21, "terms": "Applies to basic mani + pedi. Gel extras charged."},
        ],
    },
]

SHOPPERS_SEED = [
    {"phone": "918000000011", "full_name": "Aryan Verma"},
    {"phone": "918000000012", "full_name": "Sneha Joshi"},
    {"phone": "918000000013", "full_name": "Rohan Mishra"},
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def future(days: int) -> datetime:
    return now_utc() + timedelta(days=days)


def pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def make_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode()


async def get_or_create_user(
    session: AsyncSession,
    phone: str,
    full_name: str,
    role: UserRole,
) -> User:
    result = await session.execute(select(User).where(User.phone == phone))
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  ↳ User {phone} exists.")
        return existing
    user = User(
        id=uuid.uuid4(),
        phone=phone,
        full_name=full_name,
        role=role,
        is_active=True,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(user)
    await session.flush()
    print(f"  + User {phone} ({role})")
    return user


async def get_or_create_merchant(session: AsyncSession, user: User, seed: dict) -> Merchant:
    result = await session.execute(select(Merchant).where(Merchant.user_id == user.id))
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  ↳ Merchant '{seed['business_name']}' exists.")
        return existing
    merchant = Merchant(
        id=uuid.uuid4(),
        user_id=user.id,
        business_name=seed["business_name"],
        sector=seed["sector"],
        address_text=seed["address_text"],
        city=seed["city"],
        latitude=seed["latitude"],
        longitude=seed["longitude"],
        gstin=None,
        kyc_doc_url="https://via.placeholder.com/800x600.png?text=KYC+Doc",
        kyc_status=KycStatus.APPROVED,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    session.add(merchant)
    await session.flush()
    print(f"  + Merchant '{seed['business_name']}'")
    return merchant


async def seed_staff(session: AsyncSession, merchant: Merchant, seed: dict) -> None:
    result = await session.execute(
        select(MerchantStaff).where(MerchantStaff.merchant_id == merchant.id)
    )
    if result.scalar_one_or_none():
        return
    cashier_phone = seed["phone"].replace("91900", "91700")
    staff = MerchantStaff(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        staff_name=f"{seed['full_name']} (Cashier)",
        phone=cashier_phone,
        pin_hash=pin_hash("1234"),
        is_active=True,
        can_upload_reels=False,
        created_at=now_utc(),
    )
    session.add(staff)
    print(f"    + Staff {staff.staff_name}  phone={cashier_phone}  PIN=1234")


async def seed_reels_and_coupons(
    session: AsyncSession,
    merchant: Merchant,
    seed: dict,
) -> list[tuple]:
    pairs = []
    thumbnails = THUMBNAILS[seed["thumb_key"]]
    for i, (reel_seed, coupon_seed) in enumerate(zip(seed["reels"], seed["coupons"])):
        result = await session.execute(
            select(Reel).where(Reel.merchant_id == merchant.id, Reel.title == reel_seed["title"])
        )
        existing_reel = result.scalar_one_or_none()
        if existing_reel:
            result2 = await session.execute(
                select(CouponTemplate).where(CouponTemplate.reel_id == existing_reel.id)
            )
            ct = result2.scalar_one_or_none()
            if ct:
                pairs.append((existing_reel, ct))
            continue

        reel = Reel(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            title=reel_seed["title"],
            duration_seconds=28 + i * 4,
            video_url=PLACEHOLDER_VIDEO,
            thumbnail_url=thumbnails[i % len(thumbnails)],
            cloudinary_public_id=None,
            audio_type=AudioType.CAMERA_MIC,
            status=ReelStatus.APPROVED,
            views_count=100 + i * 37,
            allow_comments=True,
            expires_at=future(coupon_seed["days"] + 5),
            created_at=now_utc() - timedelta(days=i + 1),
            updated_at=now_utc(),
        )
        session.add(reel)
        await session.flush()

        ct = CouponTemplate(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            reel_id=reel.id,
            title=coupon_seed["title"],
            discount_type=coupon_seed["type"],
            discount_value=Decimal(str(coupon_seed["value"])),
            min_order_amount=Decimal(str(coupon_seed["min"])),
            validity_days=coupon_seed["days"],
            terms=coupon_seed["terms"],
            is_active=True,
            expires_at=future(coupon_seed["days"]),
            created_at=now_utc(),
        )
        session.add(ct)
        await session.flush()
        pairs.append((reel, ct))
        print(f"    + Reel '{reel.title}'  + Coupon '{ct.title}'")
    return pairs


async def seed_user_coupons(
    session: AsyncSession,
    shopper: User,
    pairs: list[tuple],
    indices: list[int],
    redeem_indices: list[int],
) -> None:
    for idx in indices:
        if idx >= len(pairs):
            continue
        _, ct = pairs[idx]
        result = await session.execute(
            select(UserCoupon).where(
                UserCoupon.coupon_template_id == ct.id,
                UserCoupon.user_id == shopper.id,
            )
        )
        if result.scalar_one_or_none():
            continue

        is_redeemed = idx in redeem_indices
        redeemed_at = now_utc() - timedelta(hours=3) if is_redeemed else None
        uc = UserCoupon(
            id=uuid.uuid4(),
            coupon_template_id=ct.id,
            user_id=shopper.id,
            status=CouponStatus.REDEEMED if is_redeemed else CouponStatus.CLAIMED,
            totp_secret=make_totp_secret(),
            claimed_at=now_utc() - timedelta(hours=6),
            expires_at=ct.expires_at,
            redeemed_at=redeemed_at,
        )
        session.add(uc)
        await session.flush()

        if is_redeemed:
            disc = (
                ct.discount_value
                if ct.discount_type == DiscountType.FLAT_AMOUNT
                else Decimal(str(round(799 * float(ct.discount_value) / 100, 2)))
            )
            ledger = RedemptionsLedger(
                id=uuid.uuid4(),
                user_coupon_id=uc.id,
                merchant_id=ct.merchant_id,
                bill_amount=Decimal("799.00"),
                discount_applied=disc,
                created_at=redeemed_at,
            )
            session.add(ledger)

        status_str = "REDEEMED" if is_redeemed else "CLAIMED"
        print(f"    + UserCoupon shopper={shopper.full_name} coupon='{ct.title}' status={status_str}")


async def main() -> None:
    print("\n🌱  Fyndo Seed Starting...\n")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            all_pairs = []
            for seed in MERCHANTS_SEED:
                print(f"\n📍 {seed['business_name']}")
                user = await get_or_create_user(session, seed["phone"], seed["full_name"], UserRole.MERCHANT)
                merchant = await get_or_create_merchant(session, user, seed)
                await seed_staff(session, merchant, seed)
                pairs = await seed_reels_and_coupons(session, merchant, seed)
                all_pairs.extend(pairs)

            print(f"\n👤 Shoppers")
            shoppers = []
            for s in SHOPPERS_SEED:
                u = await get_or_create_user(session, s["phone"], s["full_name"], UserRole.SHOPPER)
                shoppers.append(u)

            if shoppers and all_pairs:
                print(f"\n🎟️  Claiming coupons")
                await seed_user_coupons(session, shoppers[0], all_pairs, [0, 1, 4], [1])
                await seed_user_coupons(session, shoppers[1], all_pairs, [2, 6, 9], [])
                await seed_user_coupons(session, shoppers[2], all_pairs, [3, 10, 14], [3])

    print("\n✅  Seed complete!\n")
    print("=" * 60)
    print("OTP for all accounts (SMS_GATEWAY_PROVIDER=mock): 111111")
    print()
    print("Merchant logins:")
    for seed in MERCHANTS_SEED:
        print(f"  {seed['phone']}  {seed['business_name']}")
    print()
    print("Shopper logins:")
    for s in SHOPPERS_SEED:
        print(f"  {s['phone']}  {s['full_name']}")
    print()
    print("Cashier PIN: 1234  (phone: replace 9190000001x -> 9170000001x)")
    print("=" * 60)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
