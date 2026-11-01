import sys
import os
import uuid
import asyncio
from datetime import datetime, timedelta, timezone
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.database import async_session_factory
from sqlalchemy import text

def get_hash(pin: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")

async def seed_postgres():
    async with async_session_factory() as db:
        user_phone = '+919876543210'
        res = await db.execute(text('SELECT id FROM users WHERE phone = :p'), {'p': user_phone})
        row = res.fetchone()
        if row:
            user_id = row[0]
            await db.execute(text('''
                UPDATE users
                SET role = 'MERCHANT', full_name = 'The Brew House Koramangala', is_active = true, onboarding_completed = true
                WHERE id = :uid
            '''), {'uid': user_id})
        else:
            user_id = uuid.uuid4()
            await db.execute(text('''
                INSERT INTO users (id, phone, full_name, role, is_active, preferred_language, onboarding_completed, created_at, updated_at)
                VALUES (:uid, :p, 'The Brew House Koramangala', 'MERCHANT', true, 'en', true, NOW(), NOW())
            '''), {'uid': user_id, 'p': user_phone})

        cover_url = 'https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1200'
        logo_url = 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?q=80&w=300'
        kyc_doc = 'https://res.cloudinary.com/fyndo/kyc/sample_store_act.pdf'

        m_res = await db.execute(text('SELECT id FROM merchants WHERE user_id = :uid'), {'uid': user_id})
        m_row = m_res.fetchone()
        if m_row:
            merchant_id = m_row[0]
            await db.execute(text('''
                UPDATE merchants
                SET business_name = 'The Brew House Koramangala',
                    sector = 'Food & Dining',
                    address_text = '123, 5th Block, Koramangala, Bengaluru, Karnataka 560034',
                    city = 'Bengaluru',
                    latitude = 12.9352,
                    longitude = 77.6245,
                    kyc_status = 'APPROVED',
                    kyc_doc_url = :kyc,
                    cover_url = :cover,
                    logo_url = :logo,
                    profile_video_thumbnail_url = :cover,
                    subscription_status = 'ACTIVE',
                    subscription_start_date = NOW(),
                    subscription_expires_at = NOW() + INTERVAL '90 days',
                    updated_at = NOW()
                WHERE id = :mid
            '''), {'mid': merchant_id, 'cover': cover_url, 'logo': logo_url, 'kyc': kyc_doc})
        else:
            merchant_id = uuid.uuid4()
            await db.execute(text('''
                INSERT INTO merchants (id, user_id, business_name, sector, address_text, city, latitude, longitude, kyc_status, kyc_doc_url, cover_url, logo_url, profile_video_thumbnail_url, subscription_status, subscription_start_date, subscription_expires_at, call_clicks_count, created_at, updated_at)
                VALUES (:mid, :uid, 'The Brew House Koramangala', 'Food & Dining', '123, 5th Block, Koramangala, Bengaluru, Karnataka 560034', 'Bengaluru', 12.9352, 77.6245, 'APPROVED', :kyc, :cover, :logo, :cover, 'ACTIVE', NOW(), NOW() + INTERVAL '90 days', 42, NOW(), NOW())
            '''), {'mid': merchant_id, 'uid': user_id, 'cover': cover_url, 'logo': logo_url, 'kyc': kyc_doc})

        staff_phone = '+919876543211'
        pin_hash = get_hash('123456')
        s_res = await db.execute(text('SELECT id FROM merchant_staff WHERE merchant_id = :mid AND phone = :sp'), {'mid': merchant_id, 'sp': staff_phone})
        s_row = s_res.fetchone()
        if s_row:
            await db.execute(text('''
                UPDATE merchant_staff
                SET staff_name = 'Rahul (Counter Cashier)', pin_hash = :ph, is_active = true, can_upload_reels = true, can_manage_content = true
                WHERE id = :sid
            '''), {'sid': s_row[0], 'ph': pin_hash})
        else:
            staff_id = uuid.uuid4()
            await db.execute(text('''
                INSERT INTO merchant_staff (id, merchant_id, staff_name, phone, pin_hash, is_active, can_upload_reels, can_manage_content, created_at)
                VALUES (:sid, :mid, 'Rahul (Counter Cashier)', :sp, :ph, true, true, true, NOW())
            '''), {'sid': staff_id, 'mid': merchant_id, 'sp': staff_phone, 'ph': pin_hash})

        reel_res = await db.execute(text('SELECT id FROM reels WHERE merchant_id = :mid'), {'mid': merchant_id})
        reel_row = reel_res.fetchone()
        if not reel_row:
            reel_id = uuid.uuid4()
            await db.execute(text('''
                INSERT INTO reels (id, merchant_id, title, video_url, thumbnail_url, duration_seconds, views_count, status, is_expired, expires_at, allow_comments, audio_type, created_at, updated_at)
                VALUES (:rid, :mid, 'Fresh Brews & Handcrafted Pizzas', 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4', :thumb, 30, 240, 'APPROVED', false, NOW() + INTERVAL '30 days', true, 'CAMERA_MIC', NOW(), NOW())
            '''), {'rid': reel_id, 'mid': merchant_id, 'thumb': cover_url})
            coupon_id = uuid.uuid4()
            await db.execute(text('''
                INSERT INTO coupon_templates (id, merchant_id, reel_id, title, discount_type, discount_value, min_order_amount, validity_days, is_active, expires_at, created_at)
                VALUES (:cid, :mid, :rid, 'Flat 50% OFF on Fresh Brews', 'PERCENTAGE', 50, 200, 7, true, NOW() + INTERVAL '30 days', NOW())
            '''), {'cid': coupon_id, 'mid': merchant_id, 'rid': reel_id})

        await db.commit()
        print("Successfully seeded PostgreSQL merchant account and counter staff!")

if __name__ == '__main__':
    asyncio.run(seed_postgres())
