"""HTML super-admin panel (htmx + Jinja2) mounted at ``/admin``.

The panel is intentionally kept out of the OpenAPI schema: it is an operator
surface, not part of the mobile API contract.
"""
from app.admin.router import admin_router

__all__ = ["admin_router"]
