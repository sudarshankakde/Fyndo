"""Shared row, form and redirect helpers for the admin panel views."""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select

from app.admin.registry import KIND_BOOLEAN, ModelMeta, get_meta
from app.admin.utils import coerce_value, fk_options, input_value

TRUTHY = {"on", "true", "1", "yes"}


def meta_or_404(model_key: str) -> ModelMeta:
    meta = get_meta(model_key)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown table '{model_key}'.")
    return meta


def panel_context(request: Request, admin: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    """Builds the template context every panel page shares."""
    context: Dict[str, Any] = {
        "admin": admin,
        "current_path": request.url.path,
        "flash_ok": request.query_params.get("ok"),
        "flash_err": request.query_params.get("err"),
    }
    context.update(extra)
    return context


def redirect_to(request: Request, url: str) -> Response:
    """303 for full page loads; ``HX-Redirect`` when driven by htmx."""
    if request.headers.get("HX-Request"):
        return Response(status_code=200, headers={"HX-Redirect": url})
    return RedirectResponse(url, status_code=303)


async def get_row(db, meta: ModelMeta, pk_value: str):
    """Fetches one row by primary key, or raises 404."""
    attribute = getattr(meta.model, meta.pk.name)
    try:
        key = coerce_value(meta.pk, pk_value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Row not found.") from exc
    row = (await db.execute(select(meta.model).where(attribute == key))).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Row not found.")
    return row


async def form_fields(
    db,
    meta: ModelMeta,
    row: Optional[Any] = None,
    form: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Describes every editable column as a renderable field."""
    fields = []
    for column in meta.form_columns:
        if form is not None:
            raw = form.get(column.name)
        elif row is not None:
            raw = getattr(row, column.name, None)
        else:
            raw = None

        options = None
        if column.fk_table:
            options = await fk_options(db, column.fk_table)
        elif column.choices:
            options = [
                {"value": value, "label": value.replace("_", " ").title()}
                for value in column.choices
            ]

        checked = False
        if column.kind == KIND_BOOLEAN:
            checked = (
                str(raw).lower() in TRUTHY if form is not None else bool(raw)
            )
            value = ""
        elif form is not None:
            value = "" if raw is None else str(raw)
        else:
            value = input_value(column, raw)

        fields.append(
            {
                "column": column,
                "name": column.name,
                "label": column.label,
                "widget": column.widget,
                "value": value,
                "checked": checked,
                "required": column.required,
                "options": options,
                "input_type": column.input_type,
                "step": column.step,
                "fk_label": column.fk_table.replace("_", " ").rstrip("s").title()
                if column.fk_table
                else None,
            }
        )
    return fields


def apply_form(meta: ModelMeta, obj: Any, form: Any) -> List[str]:
    """Writes submitted values onto ``obj``; returns a list of human errors."""
    errors: List[str] = []
    for column in meta.form_columns:
        try:
            value = coerce_value(column, form.get(column.name))
        except ValueError:
            errors.append(f"{column.label}: that value could not be read.")
            continue
        if column.required and value is None:
            errors.append(f"{column.label} is required.")
            continue
        setattr(obj, column.name, value)
    return errors
