import asyncio
import contextlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.merchant import Merchant, MerchantStaff
from app.models.request_audit_log import RequestAuditLog
from app.models.user import User

logger = logging.getLogger("fyndo.audit_service")


_audit_queue: asyncio.Queue = asyncio.Queue(maxsize=15000)
_flusher_task: Optional[asyncio.Task] = None


async def _audit_flusher_loop() -> None:
    """Continuously drains the in-memory audit queue and bulk-persists in batches."""
    while True:
        try:
            batch: List[RequestAuditLog] = []
            item = await _audit_queue.get()
            batch.append(item)

            # Consume additional pending items up to 100 per transaction
            while len(batch) < 100 and not _audit_queue.empty():
                try:
                    batch.append(_audit_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            if batch:
                async with async_session_factory() as session:
                    session.add_all(batch)
                    await session.commit()

            for _ in batch:
                _audit_queue.task_done()
        except asyncio.CancelledError:
            # Drain remaining before exit
            while not _audit_queue.empty():
                try:
                    remaining: List[RequestAuditLog] = []
                    while len(remaining) < 100 and not _audit_queue.empty():
                        remaining.append(_audit_queue.get_nowait())
                    if remaining:
                        async with async_session_factory() as session:
                            session.add_all(remaining)
                            await session.commit()
                except Exception:
                    break
            break
        except Exception as exc:
            logger.warning("Failed to persist batched request audit logs: %s", exc)
            await asyncio.sleep(0.05)


def _ensure_flusher_task() -> None:
    global _flusher_task
    if _flusher_task is None or _flusher_task.done():
        try:
            loop = asyncio.get_running_loop()
            _flusher_task = loop.create_task(_audit_flusher_loop())
        except RuntimeError:
            pass


async def stop_audit_flusher() -> None:
    """Cancels flusher task and drains remaining queue items on server shutdown."""
    global _flusher_task
    if _flusher_task and not _flusher_task.done():
        _flusher_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _flusher_task
        _flusher_task = None


async def persist_request_audit_log(
    *,
    request_id: str,
    method: str,
    path: str,
    query_params: Optional[str],
    status_code: int,
    duration_ms: float,
    client_ip: Optional[str],
    user_agent: Optional[str],
    user_id: Optional[str],
    user_role: Optional[str],
    request_body: Optional[str],
    response_size: Optional[int],
    error_message: Optional[str],
    db_summary: Dict[str, Any],
) -> None:
    """Pushes request metadata and DB impact to the non-blocking batched flusher queue."""
    log_entry = RequestAuditLog(
        id=uuid.uuid4(),
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        method=method.upper(),
        path=path,
        query_params=query_params if query_params else None,
        status_code=status_code,
        duration_ms=duration_ms,
        client_ip=client_ip,
        user_agent=user_agent[:500] if user_agent else None,
        user_id=user_id,
        user_role=user_role,
        request_body=request_body,
        response_size=response_size,
        error_message=error_message,
        db_query_count=db_summary.get("query_count", 0),
        db_time_ms=db_summary.get("db_time_ms", 0.0),
        db_operations=db_summary.get("operations"),
        tables_affected=db_summary.get("tables_affected"),
        db_queries=db_summary.get("queries"),
    )
    _ensure_flusher_task()
    try:
        _audit_queue.put_nowait(log_entry)
    except asyncio.QueueFull:
        logger.warning("Audit queue full; dropped log entry for %s", request_id)


async def get_audit_stats(db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
    """Calculates KPI statistics across requests in the specified window."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    base_filter = RequestAuditLog.timestamp >= since

    total_requests_stmt = select(func.count(RequestAuditLog.id)).where(base_filter)
    total_requests = (await db.execute(total_requests_stmt)).scalar() or 0

    if total_requests == 0:
        return {
            "total_requests": 0,
            "error_count": 0,
            "error_rate_pct": 0.0,
            "avg_latency_ms": 0.0,
            "avg_db_time_ms": 0.0,
            "total_db_queries": 0,
            "window_hours": hours,
        }

    errors_stmt = select(func.count(RequestAuditLog.id)).where(
        base_filter, RequestAuditLog.status_code >= 400
    )
    error_count = (await db.execute(errors_stmt)).scalar() or 0

    metrics_stmt = select(
        func.avg(RequestAuditLog.duration_ms),
        func.avg(RequestAuditLog.db_time_ms),
        func.sum(RequestAuditLog.db_query_count),
    ).where(base_filter)
    avg_latency, avg_db_time, total_queries = (await db.execute(metrics_stmt)).first() or (0.0, 0.0, 0)

    error_rate = round((error_count / total_requests) * 100, 2)

    return {
        "total_requests": total_requests,
        "error_count": error_count,
        "error_rate_pct": error_rate,
        "avg_latency_ms": round(float(avg_latency or 0.0), 2),
        "avg_db_time_ms": round(float(avg_db_time or 0.0), 2),
        "total_db_queries": int(total_queries or 0),
        "window_hours": hours,
    }


async def query_audit_logs(
    db: AsyncSession,
    *,
    method: Optional[str] = None,
    status_filter: Optional[str] = None,  # 'ALL', '2XX', '4XX', '5XX', 'ERROR'
    user_role: Optional[str] = None,      # 'ALL', 'SUPER_ADMIN', 'MERCHANT', 'SHOPPER', 'ROLE_CASHIER', 'ANONYMOUS'
    search: Optional[str] = None,
    has_db_mutations: bool = False,
    min_duration_ms: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[RequestAuditLog], int, int]:
    """Queries audit logs with filtering by method, status, role, and pagination."""
    stmt = select(RequestAuditLog)

    if method and method.upper() != "ALL":
        stmt = stmt.where(RequestAuditLog.method == method.upper().strip())

    if status_filter:
        sf = status_filter.upper().strip()
        if sf == "2XX":
            stmt = stmt.where(RequestAuditLog.status_code >= 200, RequestAuditLog.status_code < 300)
        elif sf == "4XX":
            stmt = stmt.where(RequestAuditLog.status_code >= 400, RequestAuditLog.status_code < 500)
        elif sf == "5XX":
            stmt = stmt.where(RequestAuditLog.status_code >= 500)
        elif sf in ("ERROR", "ERRORS"):
            stmt = stmt.where(RequestAuditLog.status_code >= 400)

    if user_role and user_role.upper() != "ALL":
        ur = user_role.strip().upper()
        if ur in ("ANONYMOUS", "GUEST", "PUBLIC", "UNAUTHENTICATED"):
            stmt = stmt.where(or_(RequestAuditLog.user_role == None, RequestAuditLog.user_role == "ANONYMOUS", RequestAuditLog.user_role == ""))
        elif ur in ("ADMIN", "SUPER_ADMIN"):
            stmt = stmt.where(RequestAuditLog.user_role.ilike("%ADMIN%"))
        elif ur in ("MERCHANT", "STORE"):
            stmt = stmt.where(RequestAuditLog.user_role.ilike("%MERCHANT%"))
        elif ur in ("STAFF", "CASHIER", "ROLE_CASHIER"):
            stmt = stmt.where(or_(RequestAuditLog.user_role.ilike("%CASHIER%"), RequestAuditLog.user_role.ilike("%STAFF%")))
        elif ur in ("SHOPPER", "USER", "CUSTOMER"):
            stmt = stmt.where(or_(RequestAuditLog.user_role.ilike("%SHOPPER%"), RequestAuditLog.user_role.ilike("%USER%"), RequestAuditLog.user_role.ilike("%CUSTOMER%")))
        else:
            stmt = stmt.where(RequestAuditLog.user_role.ilike(f"%{ur}%"))

    if min_duration_ms and min_duration_ms > 0:
        stmt = stmt.where(RequestAuditLog.duration_ms >= min_duration_ms)

    if has_db_mutations:
        # Match logs where db_query_count > 0 and operations include INSERT, UPDATE, or DELETE
        stmt = stmt.where(RequestAuditLog.db_query_count > 0)

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                RequestAuditLog.path.ilike(term),
                RequestAuditLog.client_ip.ilike(term),
                RequestAuditLog.user_id.ilike(term),
                RequestAuditLog.user_role.ilike(term),
                RequestAuditLog.request_id.ilike(term),
            )
        )

    # Count total matching rows
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    page_count = max(1, (total_count + page_size - 1) // page_size)
    page = max(1, min(page, page_count))

    stmt = stmt.order_by(desc(RequestAuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return list(rows), total_count, page_count


async def enrich_logs_with_user_details(
    db: AsyncSession, logs: List[RequestAuditLog]
) -> Dict[str, Dict[str, Any]]:
    """Batch-fetches user and staff information for logs on the current page to display user details."""
    raw_user_ids = {log.user_id.strip() for log in logs if log.user_id and log.user_id.strip()}
    if not raw_user_ids:
        return {}

    valid_uuids: List[uuid.UUID] = []
    for uid_str in raw_user_ids:
        try:
            valid_uuids.append(uuid.UUID(uid_str))
        except (ValueError, TypeError):
            continue

    user_map: Dict[str, Dict[str, Any]] = {}
    if not valid_uuids:
        return user_map

    # Query regular users (Shoppers, Merchants, Admins)
    user_stmt = select(User).where(User.id.in_(valid_uuids))
    users = (await db.execute(user_stmt)).scalars().all()
    for u in users:
        role_val = u.role.value if hasattr(u.role, "value") else str(u.role)
        user_map[str(u.id)] = {
            "name": u.full_name or u.username or f"User {str(u.phone)[-4:]}",
            "phone": u.phone,
            "email": u.email,
            "role": role_val,
        }

    # Query staff / cashiers
    remaining_uuids = [uid for uid in valid_uuids if str(uid) not in user_map]
    if remaining_uuids:
        staff_stmt = (
            select(MerchantStaff, Merchant.business_name)
            .outerjoin(Merchant, MerchantStaff.merchant_id == Merchant.id)
            .where(MerchantStaff.id.in_(remaining_uuids))
        )
        staff_rows = (await db.execute(staff_stmt)).all()
        for staff, business_name in staff_rows:
            user_map[str(staff.id)] = {
                "name": staff.staff_name,
                "phone": staff.phone,
                "role": "ROLE_CASHIER",
                "business_name": business_name,
            }

    return user_map


async def get_audit_log_by_id(db: AsyncSession, log_id: uuid.UUID) -> Optional[RequestAuditLog]:
    """Fetches a single request audit log by UUID."""
    stmt = select(RequestAuditLog).where(RequestAuditLog.id == log_id)
    return (await db.execute(stmt)).scalars().first()

