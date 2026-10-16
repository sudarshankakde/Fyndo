"""Create, update and delete handlers for the admin panel (full CRUD)."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.deps import current_admin
from app.admin.helpers import (
    apply_form,
    form_fields,
    get_row,
    meta_or_404,
    panel_context,
    redirect_to,
)
from app.admin.templating import templates
from app.core.audit import audit_log
from app.core.database import get_db

logger = logging.getLogger("fyndo.admin")
router = APIRouter()


def _audit(admin: Dict[str, Any], action: str, meta, target_id: Any, **details: Any) -> None:
    audit_log(
        action,
        actor_id=admin.get("sub"),
        actor_role="SUPER_ADMIN",
        target_type=meta.model.__tablename__,
        target_id=target_id,
        source="admin_panel",
        **details,
    )


@router.post("/{model_key}/new")
async def create_submit(
    request: Request,
    model_key: str,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    form = await request.form()
    obj = meta.model()
    errors = apply_form(meta, obj, form)

    if not errors:
        db.add(obj)
        try:
            await db.flush()
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            logger.warning("Create rejected for %s: %s", meta.key, exc.orig)
            errors = ["The database rejected this row — check unique fields and required links."]

    if errors:
        return templates.TemplateResponse(
            request,
            "form.html",
            panel_context(
                request,
                admin,
                meta=meta,
                fields=await form_fields(db, meta, form=form),
                row_pk=None,
                errors=errors,
            ),
            status_code=422,
        )

    pk_value = getattr(obj, meta.pk.name, None)
    _audit(admin, "admin.create", meta, pk_value)
    return redirect_to(request, f"/admin/{meta.key}/{pk_value}?ok=Row+created")


@router.get("/{model_key}/{pk}/edit")
async def edit_form(
    request: Request,
    model_key: str,
    pk: str,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    row = await get_row(db, meta, pk)
    return templates.TemplateResponse(
        request,
        "form.html",
        panel_context(
            request,
            admin,
            meta=meta,
            fields=await form_fields(db, meta, row=row),
            row_pk=pk,
            errors=[],
        ),
    )


@router.post("/{model_key}/{pk}/edit")
async def edit_submit(
    request: Request,
    model_key: str,
    pk: str,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    row = await get_row(db, meta, pk)
    form = await request.form()
    errors = apply_form(meta, row, form)

    if not errors:
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            logger.warning("Update rejected for %s/%s: %s", meta.key, pk, exc.orig)
            errors = ["The database rejected this change — check unique fields and required links."]

    if errors:
        return templates.TemplateResponse(
            request,
            "form.html",
            panel_context(
                request,
                admin,
                meta=meta,
                fields=await form_fields(db, meta, form=form),
                row_pk=pk,
                errors=errors,
            ),
            status_code=422,
        )

    _audit(admin, "admin.update", meta, pk)
    return redirect_to(request, f"/admin/{meta.key}/{pk}?ok=Changes+saved")


@router.post("/{model_key}/{pk}/delete")
async def delete_submit(
    request: Request,
    model_key: str,
    pk: str,
    db: AsyncSession = Depends(get_db),
    admin: Dict[str, Any] = Depends(current_admin),
):
    meta = meta_or_404(model_key)
    row = await get_row(db, meta, pk)
    try:
        await db.delete(row)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("Delete blocked for %s/%s: %s", meta.key, pk, exc.orig)
        return redirect_to(
            request,
            f"/admin/{meta.key}/{pk}?err=This+row+is+still+referenced+by+other+records",
        )

    _audit(admin, "admin.delete", meta, pk)
    return redirect_to(request, f"/admin/{meta.key}?ok=Row+deleted")
