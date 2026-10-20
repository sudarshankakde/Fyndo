# Fyndo Backend Seed Data

## What it creates

Running `seed_data.py` populates your local PostgreSQL database with production-like demo data:

| Entity | Count | Details |
|---|---|---|
| Merchant Users | 6 | Phones: 919000000011–16 |
| Merchant Profiles | 6 | APPROVED KYC, Nagpur geo coords |
| Reels | 18 | APPROVED, 3 per merchant, Unsplash thumbnails |
| Coupon Templates | 18 | Mix of PERCENTAGE, FLAT_AMOUNT, BOGO |
| Cashier Staff | 6 | One per merchant, PIN: `1234` |
| Shopper Users | 3 | Phones: 918000000011–13 |
| User Coupons | 9 | Mix of CLAIMED and REDEEMED |
| Redemptions Ledger | 2 | Sample redemption history |

## Prerequisites

1. PostgreSQL running with the Fyndo database created
2. Python 3.10+ with venv activated

```bash
# Windows (from d:/IAOS/Fyndo/Fyndo)
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the seed

```bash
# From d:/IAOS/Fyndo/Fyndo (the repo root, NOT inside /backend)
python backend/seed_data.py
```

The script is **idempotent** — safe to run multiple times without duplicating data.

## Test Login Credentials

> OTP for all accounts (SMS gateway is `mock`): **`111111`**

### Merchant Accounts

| Phone | Business |
|---|---|
| 919000000011 | The Brew House (Café) |
| 919000000012 | Silk Route Boutique (Fashion) |
| 919000000013 | Sole Republic (Footwear) |
| 919000000014 | Gadget Galaxy (Electronics) |
| 919000000015 | Chai Pe Charcha (Food) |
| 919000000016 | Glow and Glam Salon |

### Shopper Accounts

| Phone | Name |
|---|---|
| 918000000011 | Aryan Verma (has claimed + redeemed coupons) |
| 918000000012 | Sneha Joshi (has claimed coupons) |
| 918000000013 | Rohan Mishra (has claimed + redeemed coupons) |

### Cashier Staff

Each merchant has one cashier staff. Derive phone by replacing `91900` → `91700` in the merchant phone.

| Staff Phone | Merchant |
|---|---|
| 917000000011 | The Brew House |
| 917000000012 | Silk Route Boutique |
| ... | ... |

**PIN:** `1234` for all cashier staff.

## Mobile App Configuration

Ensure your mobile `.env` / `app.config.js` points to:

```
API_BASE_URL=http://<your-local-ip>:8000
```

For Android emulator: `http://10.0.2.2:8000`  
For physical device on same WiFi: `http://192.168.x.x:8000`

### Start the backend

```bash
# From d:/IAOS/Fyndo/Fyndo
python run_dev.py
# OR
cd backend && uvicorn app.main:app --reload --port 8000
```
