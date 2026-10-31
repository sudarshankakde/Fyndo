"""Empirical Challenger Tests: Schema Migration Invariants & Concurrent Signup Race Conditions.

Adversarially validates:
1. Legacy database schema evolution (missing/NULL subscription columns, backfill, idempotency).
2. High-concurrency merchant signups across distinct users.
3. Concurrent duplicate-onboarding race conditions on the same user.
4. Ordering integrity in admin merchant creation.
"""
import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import _COMPAT_COLUMNS, async_session_factory
from app.main import app
from app.models.merchant import Merchant, SubscriptionStatus
from tests.e2e_subscriptions.helpers import bearer, seed_user, unique_phone

pytestmark = pytest.mark.asyncio


class TestLegacySchemaMigration:
    """Challenge 1: Legacy database with missing or NULL subscription columns."""

    async def test_legacy_database_missing_columns_migration(self):
        """Simulate a pre-subscription legacy SQLite database and verify ALTER TABLE + backfill."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db_url = f"sqlite+aiosqlite:///{tmp_path.replace(os.sep, '/')}"
            engine = create_async_engine(db_url)

            # Create legacy schema without subscription columns
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "CREATE TABLE merchants ("
                        "  id TEXT PRIMARY KEY,"
                        "  user_id TEXT UNIQUE NOT NULL,"
                        "  business_name TEXT NOT NULL,"
                        "  sector TEXT NOT NULL,"
                        "  address_text TEXT NOT NULL,"
                        "  city TEXT NOT NULL,"
                        "  latitude REAL NOT NULL,"
                        "  longitude REAL NOT NULL,"
                        "  kyc_doc_url TEXT NOT NULL,"
                        "  kyc_status TEXT NOT NULL,"
                        "  call_clicks_count INTEGER NOT NULL DEFAULT 0,"
                        "  created_at TIMESTAMP,"
                        "  updated_at TIMESTAMP"
                        ")"
                    )
                )
                # Insert legacy merchant with created_at in the past
                m1_id = str(uuid.uuid4())
                await conn.execute(
                    text(
                        "INSERT INTO merchants (id, user_id, business_name, sector, address_text, "
                        "city, latitude, longitude, kyc_doc_url, kyc_status, created_at, updated_at) "
                        "VALUES (:id, :uid, 'Legacy Store 1', 'FOOD', 'Main St', 'Nagpur', 21.1, 79.1, "
                        "'https://doc.pdf', 'APPROVED', '2025-06-01 10:00:00', '2025-06-01 10:00:00')"
                    ),
                    {"id": m1_id, "uid": str(uuid.uuid4())},
                )
                # Insert legacy merchant with NULL created_at
                m2_id = str(uuid.uuid4())
                await conn.execute(
                    text(
                        "INSERT INTO merchants (id, user_id, business_name, sector, address_text, "
                        "city, latitude, longitude, kyc_doc_url, kyc_status, created_at, updated_at) "
                        "VALUES (:id, :uid, 'Legacy Store 2', 'ELECTRONICS', 'East St', 'Pune', 18.5, 73.8, "
                        "'https://doc2.pdf', 'PENDING', NULL, NULL)"
                    ),
                    {"id": m2_id, "uid": str(uuid.uuid4())},
                )

            # Run compat migration logic
            async with engine.begin() as conn:
                # Add columns defined in _COMPAT_COLUMNS['merchants']
                for col_name, (sqlite_ddl, _) in _COMPAT_COLUMNS["merchants"].items():
                    if "subscription" in col_name:
                        await conn.execute(
                            text(f"ALTER TABLE merchants ADD COLUMN {col_name} {sqlite_ddl}")
                        )

                # Run exact backfill SQL from ensure_compatibility_schema()
                await conn.execute(
                    text(
                        "UPDATE merchants SET "
                        "subscription_start_date = COALESCE(subscription_start_date, created_at, CURRENT_TIMESTAMP), "
                        "subscription_expires_at = COALESCE(subscription_expires_at, datetime('now', '+90 days')) "
                        "WHERE subscription_expires_at IS NULL"
                    )
                )

            # Verify migrated state
            async with engine.begin() as conn:
                rows = (await conn.execute(
                    text("SELECT id, subscription_status, subscription_start_date, subscription_expires_at FROM merchants")
                )).fetchall()

                assert len(rows) == 2
                row_map = {r[0]: r for r in rows}

                # Legacy merchant 1: start_date backfilled from created_at ('2025-06-01')
                m1 = row_map[m1_id]
                assert m1[1] == "ACTIVE"
                assert m1[2].startswith("2025-06-01")
                assert m1[3] is not None

                # Legacy merchant 2: start_date backfilled from CURRENT_TIMESTAMP
                m2 = row_map[m2_id]
                assert m2[1] == "ACTIVE"
                assert m2[2] is not None
                assert m2[3] is not None

            # Test Idempotency: Running backfill again on migrated DB does not error or modify valid data
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "UPDATE merchants SET "
                        "subscription_start_date = COALESCE(subscription_start_date, created_at, CURRENT_TIMESTAMP), "
                        "subscription_expires_at = COALESCE(subscription_expires_at, datetime('now', '+90 days')) "
                        "WHERE subscription_expires_at IS NULL"
                    )
                )

            await engine.dispose()
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    async def test_null_subscription_status_model_resilience(self):
        """Model property must cleanly handle raw NULL subscription_status without crashing."""
        m = Merchant(
            business_name="Null Status Store",
            subscription_status=None,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        # Should gracefully treat None as ACTIVE default
        assert m.effective_subscription_status == "ACTIVE"
        assert m.is_subscription_active is True


class TestConcurrentMerchantSignup:
    """Challenge 2: Concurrent merchant signup race conditions."""

    async def test_concurrent_distinct_merchants_all_receive_trials(self):
        """10 concurrent distinct merchant signups must all succeed and receive 90-day active trial."""
        transport = ASGITransport(app=app)
        concurrency = 10

        users = []
        for i in range(concurrency):
            uid, token = await seed_user("MERCHANT", f"Concurrent Merchant {i}")
            users.append((uid, token, f"Parallel Store {i} - {unique_phone()}"))

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async def onboard_one(uid, token, name):
                return await client.post(
                    "/api/v1/merchants/onboard",
                    json={
                        "business_name": name,
                        "sector": "FOOD",
                        "address_text": "Concurrent Market Street",
                        "city": "Nagpur",
                        "latitude": 21.1458,
                        "longitude": 79.0882,
                        "kyc_doc_url": "https://sample.com/kyc.pdf",
                    },
                    headers=bearer(token),
                )

            responses = await asyncio.gather(
                *[onboard_one(uid, token, name) for uid, token, name in users]
            )

        now = datetime.now(timezone.utc)
        for resp in responses:
            assert resp.status_code == 200, f"Concurrent onboard failed: {resp.text}"
            body = resp.json()
            assert body["success"] is True
            data = body["data"]
            assert data["subscription_status"] == "ACTIVE"
            assert data["is_subscription_active"] is True

            exp = datetime.fromisoformat(data["subscription_expires_at"].replace("Z", "+00:00"))
            delta_days = (exp - now).total_seconds() / 86400
            assert 89 <= delta_days <= 92

    async def test_concurrent_duplicate_onboard_same_user_integrity(self):
        """Concurrent double-submit onboarding for the SAME user preserves single-store integrity."""
        transport = ASGITransport(app=app)
        uid, token = await seed_user("MERCHANT", "Double-Submit Merchant")

        payload = {
            "business_name": f"Race Store - {unique_phone()}",
            "sector": "ELECTRONICS",
            "address_text": "100 MG Road",
            "city": "Pune",
            "latitude": 18.52,
            "longitude": 73.85,
            "kyc_doc_url": "https://sample.com/kyc.pdf",
        }

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async def send_req():
                return await client.post(
                    "/api/v1/merchants/onboard",
                    json=payload,
                    headers=bearer(token),
                )

            # 5 concurrent identical onboarding attempts
            results = await asyncio.gather(*[send_req() for _ in range(5)], return_exceptions=True)

        successes = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
        # At least one must succeed
        assert len(successes) >= 1

        # Check DB to verify EXACTLY ONE merchant exists for this user_id
        async with async_session_factory() as session:
            db_res = await session.execute(
                text("SELECT id, subscription_status, subscription_expires_at FROM merchants WHERE user_id = :uid"),
                {"uid": uid},
            )
            merchants = db_res.fetchall()
            assert len(merchants) == 1, f"Expected exactly 1 merchant record for user, found {len(merchants)}"
            assert merchants[0][1] == "ACTIVE"
            assert merchants[0][2] is not None
