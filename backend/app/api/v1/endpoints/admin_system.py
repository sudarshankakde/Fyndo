"""System health monitoring, server resource stats, Redis metrics, and admin diagnostics."""
import os
import platform
import shutil
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin import get_current_admin
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.redis import get_redis_client
from app.models.coupon import CouponTemplate, RedemptionsLedger, UserCoupon
from app.models.merchant import Merchant, MerchantStaff
from app.models.reel import Reel
from app.models.request_audit_log import RequestAuditLog
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.services.audit_service import _audit_queue, _flusher_task, get_audit_stats

router = APIRouter()

_PROCESS_START_TIME = time.time()


def _get_system_resources() -> Dict[str, Any]:
    """Gathers CPU, memory, disk, and host runtime metrics."""
    cpu_pct = 0.0
    mem_info = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0.0}
    try:
        import psutil
        cpu_pct = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        mem_info = {
            "total_mb": round(vm.total / (1024 * 1024), 1),
            "used_mb": round(vm.used / (1024 * 1024), 1),
            "free_mb": round(vm.available / (1024 * 1024), 1),
            "percent": vm.percent,
        }
    except Exception:
        pass

    try:
        disk = shutil.disk_usage("/")
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round((disk.used / disk.total) * 100, 1),
        }
    except Exception:
        disk_info = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0.0}

    uptime_secs = int(time.time() - _PROCESS_START_TIME)
    days, rem = divmod(uptime_secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    uptime_human = f"{days}d {hours}h {mins}m {secs}s" if days > 0 else f"{hours}h {mins}m {secs}s"

    return {
        "hostname": platform.node(),
        "platform": platform.platform(terse=True),
        "os": platform.system(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
        "cpu_percent": cpu_pct,
        "memory": mem_info,
        "disk": disk_info,
        "process_id": os.getpid(),
        "uptime_seconds": uptime_secs,
        "uptime_human": uptime_human,
    }


async def _get_redis_stats() -> Dict[str, Any]:
    """Probes Redis connection, latency, memory consumption, and key hit rates."""
    start_t = time.perf_counter()
    try:
        redis = await get_redis_client()
        await redis.ping()
        latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        info = await redis.info()
        hits = int(info.get("keyspace_hits", 0))
        misses = int(info.get("keyspace_misses", 0))
        total_lookups = hits + misses
        hit_ratio = round((hits / total_lookups) * 100, 2) if total_lookups > 0 else 100.0

        return {
            "status": "connected",
            "latency_ms": latency_ms,
            "version": info.get("redis_version", "unknown"),
            "mode": info.get("redis_mode", "standalone"),
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 1),
            "used_memory_human": info.get("used_memory_human", "0M"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "0M"),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 1.0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_ratio_percent": hit_ratio,
        }
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc), "latency_ms": 0.0}


async def _get_db_stats(db: AsyncSession) -> Dict[str, Any]:
    """Probes PostgreSQL health, latency, pool sizing, and table volumes."""
    start_t = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        status_val = "connected"
    except Exception as exc:
        return {"status": f"unreachable ({exc})", "latency_ms": 0.0}

    pool = engine.pool
    pool_stats = {
        "pool_size": pool.size() if hasattr(pool, "size") else settings.DB_POOL_SIZE,
        "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else 0,
        "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else 0,
        "overflow": pool.overflow() if hasattr(pool, "overflow") else 0,
    }

    counts = {}
    for model_name, model_cls in (
        ("merchants", Merchant),
        ("users", User),
        ("reels", Reel),
        ("coupons", CouponTemplate),
        ("redemptions", RedemptionsLedger),
        ("audit_logs", RequestAuditLog),
    ):
        try:
            cnt = (await db.execute(select(func.count(model_cls.id)))).scalar() or 0
            counts[model_name] = cnt
        except Exception:
            counts[model_name] = 0

    return {
        "status": status_val,
        "latency_ms": latency_ms,
        "dialect": engine.dialect.name,
        "pool": pool_stats,
        "table_counts": counts,
    }


@router.get("/admin/system/health", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_system_health(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deep production health check: host resources, PostgreSQL pool, Redis telemetry, and queues."""
    system_res = _get_system_resources()
    redis_stats = await _get_redis_stats()
    db_stats = await _get_db_stats(db)

    audit_flusher_alive = bool(_flusher_task and not _flusher_task.done())
    overall_status = "healthy"
    if db_stats["status"] != "connected" or redis_stats["status"] != "connected":
        overall_status = "degraded"

    payload = {
        "overall_status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "service": settings.PROJECT_NAME,
        "system": system_res,
        "database": db_stats,
        "cache_redis": redis_stats,
        "subsystems": {
            "sms_gateway": {"provider": settings.SMS_GATEWAY_PROVIDER, "status": "active"},
            "push_notifications": {"enabled": settings.PUSH_ENABLED, "provider": settings.PUSH_PROVIDER},
            "cloudinary_cdn": {
                "configured": bool(settings.CLOUDINARY_CLOUD_NAME),
                "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
            },
            "audit_queue": {
                "pending_items": _audit_queue.qsize(),
                "max_size": _audit_queue.maxsize,
                "flusher_worker_active": audit_flusher_alive,
            },
        },
    }
    return ResponseEnvelope(data=payload, message=f"System is {overall_status}")


@router.get("/admin/system/metrics", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_system_metrics(
    hours: int = 24,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Performance analytics and KPI summary across the platform."""
    stats = await get_audit_stats(db, hours=hours)
    return ResponseEnvelope(data=stats, message=f"System metrics for last {hours} hours")


@router.post("/admin/system/cache/flush", response_model=ResponseEnvelope[Dict[str, Any]])
async def flush_system_cache(
    pattern: Optional[str] = "feed:*",
    admin: User = Depends(get_current_admin),
):
    """Invalidates Redis cache keys by pattern with audit logging."""
    try:
        redis = await get_redis_client()
        keys = []
        async for key in redis.scan_iter(match=pattern or "*", count=200):
            keys.append(key)
        deleted = 0
        if keys:
            deleted = await redis.delete(*keys)
        audit_log("admin.cache_flush", actor_id=admin.id, pattern=pattern, deleted_keys=deleted)
        return ResponseEnvelope(
            data={"flushed_keys": deleted, "pattern": pattern},
            message=f"Flushed {deleted} cache keys matching '{pattern}'",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flush Redis cache: {exc}",
        )


# Exported telemetry helpers for HTML admin views
get_system_resources = _get_system_resources
get_redis_stats = _get_redis_stats
get_db_stats = _get_db_stats

