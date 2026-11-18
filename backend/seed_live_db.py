import os
import sys
import uuid
import asyncio
import bcrypt
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.database import async_session_factory

def get_hash(pin: str) -> str:
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

MERCHANTS_DATA = [
    {
        "phone": "+919876543210",
        "name": "The Brew House Koramangala",
        "sector": "Food & Dining",
        "city": "Bengaluru",
        "address": "123, 5th Block, Koramangala, Bengaluru 560034",
        "lat": 12.9352,
        "lon": 77.6245,
        "cover": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1200",
        "logo": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?q=80&w=300",
        "staff_name": "Rahul Sharma",
        "staff_phone": "+919876543211",
        "staff_pin": "123456",
        "reel_title": "Fresh Brews & Handcrafted Pizzas",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "coupon_title": "Flat 50% OFF on Fresh Brews",
        "discount_type": "PERCENTAGE",
        "discount_value": 50,
        "min_order": 249,
    },
    {
        "phone": "+919876543220",
        "name": "Urban Threads Bandra",
        "sector": "Clothing & Fashion",
        "city": "Mumbai",
        "address": "45 Linking Road, Bandra West, Mumbai 400050",
        "lat": 19.0600,
        "lon": 72.8300,
        "cover": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?q=80&w=1200",
        "logo": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=300",
        "staff_name": "Pooja Patil",
        "staff_phone": "+919876543221",
        "staff_pin": "123123",
        "reel_title": "Summer Streetwear Drop - Limited Edition",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "coupon_title": "Flat ₹300 OFF on ₹1499+",
        "discount_type": "FLAT_AMOUNT",
        "discount_value": 300,
        "min_order": 1499,
    },
    {
        "phone": "+919876543230",
        "name": "NextGen Tech Hub FC Road",
        "sector": "Electronics & Mobiles",
        "city": "Pune",
        "address": "88 FC Road, Deccan Gymkhana, Pune 411004",
        "lat": 18.5204,
        "lon": 73.8567,
        "cover": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=1200",
        "logo": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?q=80&w=300",
        "staff_name": "Amit Deshmukh",
        "staff_phone": "+919876543231",
        "staff_pin": "123123",
        "reel_title": "Flagship Earbuds & Smartwatch Mega Sale",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        "coupon_title": "Buy 1 Get 1 Free Accessories",
        "discount_type": "BOGO",
        "discount_value": 100,
        "min_order": 999,
    },
    {
        "phone": "+919876543240",
        "name": "Aura Luxury Spa & Salon",
        "sector": "Food & Dining",
        "city": "Pune",
        "address": "North Main Road, Koregaon Park, Pune 411001",
        "lat": 18.5362,
        "lon": 73.8940,
        "cover": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?q=80&w=1200",
        "logo": "https://images.unsplash.com/photo-1560066984-138dadb4c035?q=80&w=300",
        "staff_name": "Neha Kulkarni",
        "staff_phone": "+919876543241",
        "staff_pin": "123456",
        "reel_title": "Rejuvenating Aromatherapy & Hair Spa",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
        "coupon_title": "Flat 35% OFF on Salon Packages",
        "discount_type": "PERCENTAGE",
        "discount_value": 35,
        "min_order": 799,
    },
]

async def seed_live():
    print("🌱 Connecting to database and seeding realistic live records...")
    async with async_session_factory() as db:
        # 1. Super Admin
        admin_phone = "+919999900000"
        res = await db.execute(text("SELECT id FROM users WHERE phone = :p"), {"p": admin_phone})
        admin_row = res.fetchone()
        if admin_row:
            await db.execute(text("""
                UPDATE users SET role = 'SUPER_ADMIN', full_name = 'Fyndo Head Admin', is_active = true, onboarding_completed = true WHERE id = :id
            """), {"id": admin_row[0]})
        else:
            await db.execute(text("""
                INSERT INTO users (id, phone, full_name, role, is_active, preferred_language, onboarding_completed, created_at, updated_at)
                VALUES (:id, :p, 'Fyndo Head Admin', 'SUPER_ADMIN', true, 'en', true, NOW(), NOW())
            """), {"id": uuid.uuid4(), "p": admin_phone})
        print("  ✓ Super Admin verified: +919999900000")

        # 2. Shopper Users
        shoppers = [
            ("+919876543290", "Aarav Sharma"),
            ("+919876543291", "Ananya Kulkarni"),
        ]
        for s_phone, s_name in shoppers:
            res = await db.execute(text("SELECT id FROM users WHERE phone = :p"), {"p": s_phone})
            if not res.fetchone():
                await db.execute(text("""
                    INSERT INTO users (id, phone, full_name, role, is_active, preferred_language, onboarding_completed, created_at, updated_at)
                    VALUES (:id, :p, :name, 'SHOPPER', true, 'en', true, NOW(), NOW())
                """), {"id": uuid.uuid4(), "p": s_phone, "name": s_name})
        print(f"  ✓ {len(shoppers)} Shopper accounts ready")

        # 3. Merchants, Staff, Reels & Coupons
        for m in MERCHANTS_DATA:
            u_res = await db.execute(text("SELECT id FROM users WHERE phone = :p"), {"p": m["phone"]})
            u_row = u_res.fetchone()
            if u_row:
                user_id = u_row[0]
                await db.execute(text("""
                    UPDATE users SET role = 'MERCHANT', full_name = :name, is_active = true, onboarding_completed = true WHERE id = :uid
                """), {"name": m["name"], "uid": user_id})
            else:
                user_id = uuid.uuid4()
                await db.execute(text("""
                    INSERT INTO users (id, phone, full_name, role, is_active, preferred_language, onboarding_completed, created_at, updated_at)
                    VALUES (:uid, :p, :name, 'MERCHANT', true, 'en', true, NOW(), NOW())
                """), {"uid": user_id, "p": m["phone"], "name": m["name"]})

            # Merchant Profile
            m_res = await db.execute(text("SELECT id FROM merchants WHERE user_id = :uid"), {"uid": user_id})
            m_row = m_res.fetchone()
            if m_row:
                merchant_id = m_row[0]
                await db.execute(text("""
                    UPDATE merchants SET
                        business_name = :bname, sector = :sec, address_text = :addr, city = :city,
                        latitude = :lat, longitude = :lon, kyc_status = 'APPROVED', cover_url = :cover,
                        logo_url = :logo, subscription_status = 'ACTIVE', updated_at = NOW()
                    WHERE id = :mid
                """), {
                    "mid": merchant_id, "bname": m["name"], "sec": m["sector"], "addr": m["address"],
                    "city": m["city"], "lat": m["lat"], "lon": m["lon"], "cover": m["cover"], "logo": m["logo"]
                })
            else:
                merchant_id = uuid.uuid4()
                await db.execute(text("""
                    INSERT INTO merchants (
                        id, user_id, business_name, sector, address_text, city, latitude, longitude,
                        kyc_status, kyc_doc_url, cover_url, logo_url, profile_video_thumbnail_url,
                        subscription_status, subscription_start_date, subscription_expires_at,
                        call_clicks_count, created_at, updated_at
                    ) VALUES (
                        :mid, :uid, :bname, :sec, :addr, :city, :lat, :lon,
                        'APPROVED', 'https://res.cloudinary.com/fyndo/kyc/sample.pdf',
                        :cover, :logo, :cover, 'ACTIVE', NOW(), NOW() + INTERVAL '90 days',
                        28, NOW(), NOW()
                    )
                """), {
                    "mid": merchant_id, "uid": user_id, "bname": m["name"], "sec": m["sector"],
                    "addr": m["address"], "city": m["city"], "lat": m["lat"], "lon": m["lon"],
                    "cover": m["cover"], "logo": m["logo"]
                })

            # Counter Staff
            pin_hash = get_hash(m["staff_pin"])
            st_res = await db.execute(text("SELECT id FROM merchant_staff WHERE merchant_id = :mid AND phone = :p"), {
                "mid": merchant_id, "p": m["staff_phone"]
            })
            st_row = st_res.fetchone()
            if st_row:
                await db.execute(text("""
                    UPDATE merchant_staff SET staff_name = :sname, pin_hash = :ph, is_active = true,
                        can_upload_reels = true, can_manage_content = true WHERE id = :sid
                """), {"sid": st_row[0], "sname": m["staff_name"], "ph": pin_hash})
            else:
                await db.execute(text("""
                    INSERT INTO merchant_staff (id, merchant_id, staff_name, phone, pin_hash, is_active, can_upload_reels, can_manage_content, created_at)
                    VALUES (:sid, :mid, :sname, :p, :ph, true, true, true, NOW())
                """), {"sid": uuid.uuid4(), "mid": merchant_id, "sname": m["staff_name"], "p": m["staff_phone"], "ph": pin_hash})

            # Video Reel & Discount Coupon
            r_res = await db.execute(text("SELECT id FROM reels WHERE merchant_id = :mid"), {"mid": merchant_id})
            r_row = r_res.fetchone()
            if not r_row:
                reel_id = uuid.uuid4()
                await db.execute(text("""
                    INSERT INTO reels (
                        id, merchant_id, title, video_url, thumbnail_url, duration_seconds, views_count,
                        status, is_expired, expires_at, allow_comments, audio_type, created_at, updated_at
                    ) VALUES (
                        :rid, :mid, :title, :vurl, :thumb, 30, 185, 'APPROVED', false,
                        NOW() + INTERVAL '30 days', true, 'CAMERA_MIC', NOW(), NOW()
                    )
                """), {"rid": reel_id, "mid": merchant_id, "title": m["reel_title"], "vurl": m["video_url"], "thumb": m["cover"]})

                await db.execute(text("""
                    INSERT INTO coupon_templates (
                        id, merchant_id, reel_id, title, discount_type, discount_value, min_order_amount,
                        validity_days, is_active, expires_at, created_at
                    ) VALUES (
                        :cid, :mid, :rid, :title, :dtype, :dval, :minord, 14, true, NOW() + INTERVAL '30 days', NOW()
                    )
                """), {
                    "cid": uuid.uuid4(), "mid": merchant_id, "rid": reel_id, "title": m["coupon_title"],
                    "dtype": m["discount_type"], "dval": m["discount_value"], "minord": m["min_order"]
                })
            print(f"  ✓ Store & Reel seeded: {m['name']} ({m['city']})")

        await db.commit()
    print("\n🎉 Live Database successfully seeded with Admins, Merchants, Staff, Reels & Vouchers!")

if __name__ == "__main__":
    asyncio.run(seed_live())
