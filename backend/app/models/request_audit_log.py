"""Model for recording production-level HTTP request logs and their database effects."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RequestAuditLog(Base):
    """Stores full audit traces of inbound requests, client details, and database queries."""

    __tablename__ = "request_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    method: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    path: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    query_params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # Client details
    client_ip: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)

    # Request payload & response info
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Database Impact Metrics
    db_query_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    db_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    db_operations: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    tables_affected: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    db_queries: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

