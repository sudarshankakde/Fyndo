"""Database query tracker that records SQL queries executed during each HTTP request.

Leverages SQLAlchemy engine events and contextvars to provide zero-overhead,
asynchronous request-scoped database query and impact profiling.
"""
import re
import time
from contextvars import ContextVar
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import event

from app.core.database import engine

# Context variable that holds the list of DB queries for the current request
request_db_queries_ctx: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "request_db_queries_ctx", default=None
)

_TABLE_PATTERNS = [
    re.compile(r"\bFROM\s+[\"`]?([a-zA-Z0-9_]+)[\"`]?", re.IGNORECASE),
    re.compile(r"\bINTO\s+[\"`]?([a-zA-Z0-9_]+)[\"`]?", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+[\"`]?([a-zA-Z0-9_]+)[\"`]?", re.IGNORECASE),
    re.compile(r"\bTABLE\s+[\"`]?([a-zA-Z0-9_]+)[\"`]?", re.IGNORECASE),
]

_OP_PATTERN = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|COMMIT|ROLLBACK|BEGIN)", re.IGNORECASE)


def parse_sql_impact(statement: str) -> Tuple[str, Optional[str]]:
    """Quickly extracts operation type and primary affected table from a SQL statement."""
    clean_sql = statement.strip()
    op_match = _OP_PATTERN.match(clean_sql)
    operation = op_match.group(1).upper() if op_match else "SQL"

    primary_table = None
    for pattern in _TABLE_PATTERNS:
        match = pattern.search(clean_sql)
        if match:
            table_candidate = match.group(1).lower()
            if table_candidate not in ("select", "where", "from", "values", "join", "inner", "left"):
                primary_table = table_candidate
                break

    return operation, primary_table


def start_tracking_db_queries() -> None:
    """Activates database query capturing for the current asyncio request task."""
    request_db_queries_ctx.set([])


def stop_tracking_db_queries() -> List[Dict[str, Any]]:
    """Stops capturing and returns all recorded queries for the current request."""
    queries = request_db_queries_ctx.get() or []
    request_db_queries_ctx.set(None)
    return queries


def summarize_db_impact(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarizes query execution counts, operations, and tables affected."""
    if not queries:
        return {
            "query_count": 0,
            "db_time_ms": 0.0,
            "operations": {},
            "tables_affected": [],
            "queries": [],
        }

    operations: Dict[str, int] = {}
    tables = set()
    total_time = 0.0

    for q in queries:
        op = q.get("operation", "SQL")
        operations[op] = operations.get(op, 0) + 1
        tbl = q.get("table")
        if tbl:
            tables.add(tbl)
        total_time += q.get("duration_ms", 0.0)

    return {
        "query_count": len(queries),
        "db_time_ms": round(total_time, 2),
        "operations": operations,
        "tables_affected": sorted(list(tables)),
        "queries": queries[:50],  # Cap per-request logged statements to 50 for safety
    }


# Register SQLAlchemy core event listeners
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if request_db_queries_ctx.get() is not None:
        context._query_start_time = time.perf_counter()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    queries_list = request_db_queries_ctx.get()
    if queries_list is not None:
        start_time = getattr(context, "_query_start_time", None)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2) if start_time else 0.0

        op, table = parse_sql_impact(statement)
        row_count = cursor.rowcount if hasattr(cursor, "rowcount") and cursor.rowcount >= 0 else None

        queries_list.append({
            "sql": statement[:600],
            "duration_ms": duration_ms,
            "operation": op,
            "table": table,
            "rows": row_count,
        })


@event.listens_for(engine.sync_engine, "handle_error")
def _handle_error(exception_context):
    queries_list = request_db_queries_ctx.get()
    if queries_list is not None:
        statement = getattr(exception_context, "statement", "") or ""
        op, table = parse_sql_impact(statement)
        queries_list.append({
            "sql": statement[:600],
            "duration_ms": 0.0,
            "operation": op,
            "table": table,
            "error": str(exception_context.original_exception)[:200],
        })

