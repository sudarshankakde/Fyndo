import uuid
from datetime import datetime, timedelta, timezone
import sqlite3
import bcrypt

def get_hash(pin: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")

conn = sqlite3.connect('fyndo_dev.db')
c = conn.cursor()

# 1. Update/ensure merchant user
user_phone = '+919876543210'
c.execute("SELECT id FROM users WHERE phone = ?", (user_phone,))
user_row = c.fetchone()

if user_row:
    user_id = user_row[0]
    c.execute("""
        UPDATE users 
        SET role = 'MERCHANT', full_name = 'The Brew House', is_active = 1
        WHERE id = ?
    """, (user_id,))
else:
    user_id = uuid.uuid4().hex
    c.execute("""
        INSERT INTO users (id, phone, full_name, role, is_active, preferred_language, created_at, updated_at)
        VALUES (?, ?, 'The Brew House', 'MERCHANT', 1, 'en', datetime('now'), datetime('now'))
    """, (user_id, user_phone))

# 2. Update/ensure merchant profile
c.execute("SELECT id FROM merchants WHERE user_id = ?", (user_id,))
m_row = c.fetchone()

cover_url = 'https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1200'
logo_url = 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?q=80&w=300'

if m_row:
    merchant_id = m_row[0]
    c.execute("""
        UPDATE merchants
        SET business_name = 'The Brew House',
            sector = 'Food & Dining',
            address_text = '123, 5th Block, Koramangala, Bengaluru, Karnataka 560034',
            city = 'Bengaluru',
            latitude = 12.9352,
            longitude = 77.6245,
            kyc_status = 'APPROVED',
            profile_video_thumbnail_url = ?,
            call_clicks_count = 42,
            updated_at = datetime('now')
        WHERE id = ?
    """, (cover_url, merchant_id))
else:
    merchant_id = uuid.uuid4().hex
    c.execute("""
        INSERT INTO merchants (id, user_id, business_name, sector, address_text, city, latitude, longitude, kyc_status, profile_video_thumbnail_url, call_clicks_count, created_at, updated_at)
        VALUES (?, ?, 'The Brew House', 'Food & Dining', '123, 5th Block, Koramangala, Bengaluru, Karnataka 560034', 'Bengaluru', 12.9352, 77.6245, 'APPROVED', ?, 42, datetime('now'), datetime('now'))
    """, (merchant_id, user_id, cover_url))

# 3. Approve reels and set future expiry
future_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
c.execute("""
    UPDATE reels
    SET status = 'APPROVED',
        is_expired = 0,
        expires_at = ?,
        deleted_at = NULL,
        views_count = CASE WHEN views_count = 0 THEN 240 ELSE views_count END
    WHERE merchant_id = ?
""", (future_date, merchant_id))

# 4. Set future expiry for coupons
c.execute("""
    UPDATE coupon_templates
    SET is_active = 1,
        expires_at = ?
    WHERE merchant_id = ?
""", (future_date, merchant_id))

# 5. Add or update counter staff
staff_phone = '+919876543211'
c.execute("SELECT id FROM merchant_staff WHERE merchant_id = ? AND phone = ?", (merchant_id, staff_phone))
staff_row = c.fetchone()
pin_hash = get_hash('123456')

if staff_row:
    c.execute("""
        UPDATE merchant_staff
        SET staff_name = 'Rahul (Counter Cashier)',
            pin_hash = ?,
            is_active = 1,
            can_upload_reels = 1
        WHERE id = ?
    """, (pin_hash, staff_row[0]))
else:
    staff_id = uuid.uuid4().hex
    c.execute("""
        INSERT INTO merchant_staff (id, merchant_id, staff_name, phone, pin_hash, is_active, can_upload_reels, created_at)
        VALUES (?, ?, 'Rahul (Counter Cashier)', ?, ?, 1, 1, datetime('now'))
    """, (staff_id, merchant_id, staff_phone, pin_hash))

conn.commit()
conn.close()
print("Successfully seeded merchant account and counter staff!")
