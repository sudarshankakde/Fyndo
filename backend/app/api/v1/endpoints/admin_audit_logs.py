"""Admin endpoints for retrieving and inspecting HTTP & database request audit logs."""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin import get_current_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.services.audit_service import (
    enrich_logs_with_user_details,
    get_audit_log_by_id,
    get_audit_stats,
    query_audit_logs,
)

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin Audit Logs"])


@router.get("", response_model=ResponseEnvelope[Dict[str, Any]])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    method: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db_only: bool = Query(False),
    min_duration_ms: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Fetches paginated request audit logs with client metadata, user details, and DB metrics."""
    logs, total_count, page_count = await query_audit_logs(
        db,
        method=method,
        status_filter=status_filter,
        user_role=user_role,
        search=search,
        has_db_mutations=db_only,
        min_duration_ms=min_duration_ms,
        page=page,
        page_size=page_size,
    )
    stats = await get_audit_stats(db, hours=24)
    user_map = await enrich_logs_with_user_details(db, logs)

    serialized_logs = [
        {
            "id": str(log.id),
            "request_id": log.request_id,
            "timestamp": log.timestamp.isoformat(),
            "method": log.method,
            "path": log.path,
            "query_params": log.query_params,
            "status_code": log.status_code,
            "duration_ms": log.duration_ms,
            "client_ip": log.client_ip,
            "user_agent": log.user_agent,
            "user_id": log.user_id,
            "user_role": log.user_role,
            "user_details": user_map.get(str(log.user_id)) if log.user_id else None,
            "request_body": log.request_body,
            "response_size": log.response_size,
            "error_message": log.error_message,
            "db_query_count": log.db_query_count,
            "db_time_ms": log.db_time_ms,
            "db_operations": log.db_operations or {},
            "tables_affected": log.tables_affected or [],
            "db_queries": log.db_queries or [],
        }
        for log in logs
    ]

    return ResponseEnvelope(
        data={
            "logs": serialized_logs,
            "total_count": total_count,
            "page_count": page_count,
            "current_page": page,
            "stats": stats,
        }
    )


@router.get("/stats", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_audit_log_stats(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Returns aggregated traffic and database execution metrics."""
    stats = await get_audit_stats(db, hours=hours)
    return ResponseEnvelope(data=stats)


@router.get("/{log_id}", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_audit_log_detail(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> ResponseEnvelope[Dict[str, Any]]:
    """Returns detailed trace of a single request including individual SQL statements."""
    log = await get_audit_log_by_id(db, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log record not found.",
        )

    user_map = await enrich_logs_with_user_details(db, [log])
    return ResponseEnvelope(
        data={
            "id": str(log.id),
            "request_id": log.request_id,
            "timestamp": log.timestamp.isoformat(),
            "method": log.method,
            "path": log.path,
            "query_params": log.query_params,
            "status_code": log.status_code,
            "duration_ms": log.duration_ms,
            "client_ip": log.client_ip,
            "user_agent": log.user_agent,
            "user_id": log.user_id,
            "user_role": log.user_role,
            "user_details": user_map.get(str(log.user_id)) if log.user_id else None,
            "request_body": log.request_body,
            "response_size": log.response_size,
            "error_message": log.error_message,
            "db_query_count": log.db_query_count,
            "db_time_ms": log.db_time_ms,
            "db_operations": log.db_operations or {},
            "tables_affected": log.tables_affected or [],
            "db_queries": log.db_queries or [],
        }
    )

