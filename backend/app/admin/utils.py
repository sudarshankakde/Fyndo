"""Value formatting, form coercion and query helpers for the admin panel."""
import json
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import String, cast, func, or_, select

from app.admin.registry import (
    KIND_BOOLEAN,
    KIND_DATETIME,
    KIND_INTEGER,
    KIND_JSON,
    KIND_NUMBER,
    KIND_UUID,
    REGISTRY_BY_TABLE,
    ColumnMeta,
    ModelMeta,
)

EMPTY = "—"

# Fallback display fields tried in order when a model has no label_column.
_DISPLAY_CANDIDATES = (
    "business_name",
    "staff_name",
    "title",
    "full_name",
    "name",
    "event_type",
    "phone",
    "email",
    "username",
    "city",
)


# --------------------------------------------------------------------- output
def truncate(value: str, limit: int = 64) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_value(column: ColumnMeta, value: Any) -> str:
    """Renders a database value as display text (templates escape it)."""
    if value is None or value == "":
        return EMPTY
    if column.kind == KIND_BOOLEAN:
        return "Yes" if value else "No"
    if column.kind == KIND_DATETIME:
        try:
            return value.strftime("%d %b %Y, %H:%M")
        except AttributeError:
            return str(value)
    if column.kind == KIND_JSON:
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return truncate(str(value), 120)


def input_value(column: ColumnMeta, value: Any) -> str:
    """Renders a value so it round-trips through an HTML form control."""
    if value is None:
        return ""
    if column.kind == KIND_DATETIME:
        try:
            return value.strftime("%Y-%m-%dT%H:%M")
        except AttributeError:
            return str(value)
    if column.kind == KIND_JSON:
        try:
            return json.dumps(value, indent=2, default=str)
        except (TypeError, ValueError):
            return str(value)
    if column.kind == KIND_UUID:
        return str(value)
    return str(value)


def row_display(meta: ModelMeta, row: Any) -> str:
    candidates: Sequence[Optional[str]] = (meta.label_column, *_DISPLAY_CANDIDATES)
    for name in candidates:
        if not name:
            continue
        value = getattr(row, name, None)
        if value:
            return truncate(str(value), 44)
    pk_value = getattr(row, meta.pk.name, None)
    return str(pk_value)[:8] if pk_value else "—"


def serialize_row(meta: ModelMeta, row: Any) -> Dict[str, Any]:
    pk_value = getattr(row, meta.pk.name, None)
    cells = []
    for column in meta.list_column_metas:
        raw = getattr(row, column.name, None)
        cells.append(
            {
                "name": column.name,
                "label": column.label,
                "text": format_value(column, raw),
                "is_bool": column.kind == KIND_BOOLEAN,
                "flag": bool(raw) if column.kind == KIND_BOOLEAN else False,
                "is_empty": raw is None or raw == "",
            }
        )
    return {
        "pk": str(pk_value) if pk_value is not None else "",
        "display": row_display(meta, row),
        "cells": cells,
    }


def serialize_detail(meta: ModelMeta, row: Any) -> List[Dict[str, Any]]:
    fields = []
    for column in meta.columns:
        raw = getattr(row, column.name, None)
        fields.append(
            {
                "label": column.label,
                "name": column.name,
                "text": format_value(column, raw),
                "is_bool": column.kind == KIND_BOOLEAN,
                "flag": bool(raw) if column.kind == KIND_BOOLEAN else False,
                "is_empty": raw is None or raw == "",
                "is_json": column.kind == KIND_JSON and raw is not None,
            }
        )
    return fields


# ---------------------------------------------------------------------- input
def parse_datetime(raw: str) -> datetime:
    text = str(raw).strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            value = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    else:
        value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def coerce_value(column: ColumnMeta, raw: Any) -> Any:
    """Converts a raw form value into the Python type the column expects."""
    if column.kind == KIND_BOOLEAN:
        return str(raw).lower() in {"on", "true", "1", "yes"}

    if raw is None:
        return None
    text = raw.strip() if isinstance(raw, str) else raw
    if text == "":
        return None

    try:
        if column.kind == KIND_INTEGER:
            return int(Decimal(str(text)))
        if column.kind == KIND_NUMBER:
            return Decimal(str(text))
        if column.kind == KIND_UUID:
            return uuid.UUID(str(text))
        if column.kind == KIND_DATETIME:
            return parse_datetime(str(text))
        if column.kind == KIND_JSON:
            return json.loads(str(text))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(str(exc)) from exc
    return text


# ---------------------------------------------------------------------- query
async def fk_options(db, target_table: str, limit: int = 500) -> List[Dict[str, str]]:
    """Loads picker options for a foreign-key column."""
    target = REGISTRY_BY_TABLE.get(target_table)
    if not target:
        return []
    stmt = select(target.model)
    order_column = target.label_column or "created_at"
    attribute = getattr(target.model, order_column, None)
    if attribute is not None:
        stmt = stmt.order_by(attribute.asc())
    rows = (await db.execute(stmt.limit(limit))).scalars().all()
    options = []
    for row in rows:
        pk_value = getattr(row, target.pk.name, None)
        if pk_value is None:
            continue
        options.append({"value": str(pk_value), "label": row_display(target, row)})
    return options


async def query_page(
    db,
    meta: ModelMeta,
    search: str = "",
    sort: str = "",
    desc: bool = True,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Any], int, int, int]:
    """Returns ``(rows, total, page_count, page)`` for the list view."""
    model = meta.model
    stmt = select(model)
    count_stmt = select(func.count()).select_from(model)

    term = (search or "").strip()
    if term and meta.search_columns:
        clauses = []
        for name in meta.search_columns:
            attribute = getattr(model, name, None)
            if attribute is not None:
                clauses.append(cast(attribute, String).ilike(f"%{term}%"))
        if clauses:
            condition = or_(*clauses)
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

    sort_name = sort if sort and meta.column(sort) else meta.sort_column
    sort_attribute = getattr(model, sort_name, None)
    if sort_attribute is not None:
        stmt = stmt.order_by(sort_attribute.desc() if desc else sort_attribute.asc())

    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    page_count = max(1, math.ceil(total / page_size))
    page = min(page, page_count)

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total, page_count, page


async def count_rows(db, meta: ModelMeta) -> int:
    return int((await db.execute(select(func.count()).select_from(meta.model))).scalar_one() or 0)
