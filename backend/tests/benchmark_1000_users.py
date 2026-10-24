"""High-Concurrency 1,000 Requests/Min Load Benchmark for Fyndo.

Simulates 1,000 user actions arriving concurrently:
  * 500 Proximity Feed queries (testing shared Redis grid cache)
  * 300 View recordings (testing Redis deduplication & atomic count increment)
  * 100 Likes toggle (testing user state hydration & counter)
  * 100 Comments queries (testing indexed fetch)

Measures latency percentiles (p50, p90, p95, p99), throughput (RPS), and error rates.
"""
import asyncio
import os
import random
import sys
import time
import uuid
from typing import Dict, List, Tuple
from httpx import ASGITransport, AsyncClient

# Add project root to sys.path so app imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, engine, ensure_compatibility_schema, async_session_factory
from app.models.coupon import CouponTemplate, DiscountType
from app.models.merchant import KycStatus, Merchant, Sector
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User, UserRole
from app.main import app


async def _setup_benchmark_data(db) -> Tuple[List[uuid.UUID], List[str]]:
    """Seeds test merchants and reels, returning reel IDs and user auth tokens."""
    # Ensure schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_compatibility_schema()

    reel_ids: List[uuid.UUID] = []
    # Seed 5 merchants and 10 reels in Nagpur
    for m_idx in range(5):
        merchant_user = User(
            phone=f"+9198{random.randint(10000000, 99999999)}",
            role=UserRole.MERCHANT
        )
        db.add(merchant_user)
        await db.flush()

        merchant = Merchant(
            user_id=merchant_user.id,
            business_name=f"Benchmark Store {m_idx}",
            sector=Sector.FOOD if m_idx % 2 == 0 else Sector.FASHION,
            city="Nagpur",
            address_text=f"Dharampeth Ward {m_idx}, Nagpur",
            latitude=21.1458 + (m_idx * 0.005),
            longitude=79.0882 + (m_idx * 0.005),
            kyc_doc_url="https://res.cloudinary.com/fyndo/kyc/doc.pdf",
            kyc_status=KycStatus.APPROVED,
        )
        db.add(merchant)
        await db.flush()

        for r_idx in range(2):
            reel = Reel(
                merchant_id=merchant.id,
                title=f"Delicious Special Deal #{m_idx}-{r_idx}",
                video_url=f"https://res.cloudinary.com/fyndo/video/upload/v1700000000/fyndo/reels/reel_{m_idx}_{r_idx}.mp4",
                video_hls_url=f"https://res.cloudinary.com/fyndo/video/upload/sp_auto/fyndo/reels/reel_{m_idx}_{r_idx}.m3u8",
                thumbnail_url=f"https://res.cloudinary.com/fyndo/image/upload/v1700000000/fyndo/reels/thumb_{m_idx}_{r_idx}.webp",
                duration_seconds=30,
                audio_type=AudioType.CAMERA_MIC,
                status=ReelStatus.APPROVED,
                allow_comments=True,
            )
            db.add(reel)
            await db.flush()
            reel_ids.append(reel.id)

            coupon = CouponTemplate(
                merchant_id=merchant.id,
                reel_id=reel.id,
                title=f"{10 + m_idx * 5}% Off Today",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=10.0 + m_idx * 5,
                validity_days=5,
                is_active=True,
            )
            db.add(coupon)
            await db.flush()

    await db.commit()
    return reel_ids


async def run_benchmark(concurrency: int = 50, total_requests: int = 1000):
    print("=" * 70)
    print(f"  FYNDO HIGH-CONCURRENCY BENCHMARK: {total_requests} REQUESTS")
    print(f"  Concurrency Level: {concurrency} parallel async workers")
    print("=" * 70)

    async with async_session_factory() as db:
        reel_ids = await _setup_benchmark_data(db)

    print(f"[*] Benchmark data prepared: {len(reel_ids)} active reels ready.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://benchmark") as client:
        # Pre-login 20 distinct users to test authenticated operations
        tokens = []
        for i in range(20):
            phone = f"+9199{random.randint(10000000, 99999999)}"
            send = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
            otp = send.json()["data"]["test_otp"]
            verify = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
            tokens.append(verify.json()["data"]["access_token"])

        print(f"[*] Pre-authenticated {len(tokens)} simulated shopper accounts.")

        # Prepare request plan: 500 feeds, 300 views, 100 likes, 100 comments = 1000 total
        tasks_plan = []
        for _ in range(500):
            tasks_plan.append(("FEED", "/api/v1/reels/feed?lat=21.1458&lon=79.0882&radius_km=10", "GET", None))
        for _ in range(300):
            rid = random.choice(reel_ids)
            tasks_plan.append(("VIEW", f"/api/v1/reels/{rid}/view", "POST", None))
        for _ in range(100):
            rid = random.choice(reel_ids)
            tasks_plan.append(("LIKE", f"/api/v1/reels/{rid}/like", "POST", None))
        for _ in range(100):
            rid = random.choice(reel_ids)
            tasks_plan.append(("COMMENT", f"/api/v1/reels/{rid}/comments", "GET", None))

        random.shuffle(tasks_plan)

        semaphore = asyncio.Semaphore(concurrency)
        latencies: Dict[str, List[float]] = {
            "FEED": [],
            "VIEW": [],
            "LIKE": [],
            "COMMENT": [],
            "ALL": [],
        }
        status_codes: Dict[int, int] = {}

        async def worker(op_type: str, path: str, method: str):
            async with semaphore:
                token = random.choice(tokens)
                device_id = str(uuid.uuid4())
                headers = {
                    "Authorization": f"Bearer {token}",
                    "X-Device-ID": device_id,
                }
                start_t = time.perf_counter()
                try:
                    if method == "GET":
                        resp = await client.get(path, headers=headers)
                    else:
                        resp = await client.post(path, headers=headers)
                    duration_ms = (time.perf_counter() - start_t) * 1000.0
                    status = resp.status_code
                except Exception as exc:
                    duration_ms = (time.perf_counter() - start_t) * 1000.0
                    status = 500

                latencies[op_type].append(duration_ms)
                latencies["ALL"].append(duration_ms)
                status_codes[status] = status_codes.get(status, 0) + 1

        # Mute noisy SQL engine logs during high-volume benchmark
        import logging
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("fyndo").setLevel(logging.WARNING)

        print(f"[*] Dispatching {len(tasks_plan)} requests across {concurrency} workers...")
        wall_start = time.perf_counter()
        await asyncio.gather(*(worker(op, path, method) for op, path, method, _ in tasks_plan))
        wall_elapsed = time.perf_counter() - wall_start

    rps = total_requests / wall_elapsed

    def calc_percentiles(times: List[float]):
        if not times:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        s = sorted(times)
        p50 = s[int(len(s) * 0.50)]
        p90 = s[int(len(s) * 0.90)]
        p95 = s[int(len(s) * 0.95)]
        p99 = s[min(int(len(s) * 0.99), len(s) - 1)]
        avg = sum(s) / len(s)
        return avg, p50, p90, p95, p99

    print("\n" + "=" * 70)
    print("  BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total Requests Completed : {total_requests}")
    print(f"  Total Wall Clock Time    : {wall_elapsed:.2f} seconds")
    print(f"  Sustained Throughput     : {rps:.1f} Requests / Second")
    print(f"  Capacity (Req/Minute)    : {rps * 60.0:.0f} Requests / Minute")
    print("-" * 70)
    print("  Status Code Distribution :")
    for code, count in sorted(status_codes.items()):
        pct = (count / total_requests) * 100
        print(f"    HTTP {code} : {count} ({pct:.1f}%)")
    print("-" * 70)
    print("  Latency Percentiles (in milliseconds):")
    print(f"  {'Operation':<10} {'Reqs':<6} {'Avg':<8} {'p50':<8} {'p90':<8} {'p95':<8} {'p99':<8}")
    print("  " + "-" * 62)
    for op in ["FEED", "VIEW", "LIKE", "COMMENT", "ALL"]:
        times = latencies[op]
        avg, p50, p90, p95, p99 = calc_percentiles(times)
        print(f"  {op:<10} {len(times):<6} {avg:<8.2f} {p50:<8.2f} {p90:<8.2f} {p95:<8.2f} {p99:<8.2f}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmark(concurrency=50, total_requests=1000))
