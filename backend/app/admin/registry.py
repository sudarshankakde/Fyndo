"""Introspection engine that turns SQLAlchemy mappers into panel descriptors.

The panel never hard-codes table knowledge: every list, form and detail view is
driven by the :class:`ModelMeta` objects produced here. Per-model overrides live
in :mod:`app.admin.configs`; anything not overridden is inferred from the mapper.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    inspect as sa_inspect,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app import models  # noqa: F401  (registers every mapper on Base)
from app.admin.configs import MODEL_CONFIGS

# Column "kinds" drive both the widget rendered in a form and the way a raw
# string from the browser is coerced before it touches the database.
KIND_TEXT = "text"
KIND_INTEGER = "integer"
KIND_NUMBER = "number"
KIND_BOOLEAN = "boolean"
KIND_DATETIME = "datetime"
KIND_JSON = "json"
KIND_UUID = "uuid"

# Acronyms and FK/date columns read poorly with a naive title-case.
LABEL_OVERRIDES = {
    "id": "ID",
    "gstin": "GSTIN",
    "kyc_status": "KYC Status",
    "kyc_doc_url": "KYC Document",
    "kyc_rejection_reason": "KYC Rejection Reason",
    "totp_secret": "TOTP Secret",
    "pin_hash": "PIN Hash",
    "password_hash": "Password Hash",
    "cloudinary_public_id": "Cloudinary Public ID",
    "user_id": "User",
    "merchant_id": "Merchant",
    "reel_id": "Reel",
    "staff_id": "Staff",
    "user_coupon_id": "Claimed Coupon",
    "coupon_template_id": "Coupon Template",
    "redeemed_by_staff_id": "Redeemed By Staff",
    "parent_comment_id": "Parent Comment",
    "is_active": "Active",
    "is_read": "Read",
    "push_sent": "Push Sent",
    "allow_comments": "Comments Allowed",
    "views_count": "Views",
    "distance_from_shop_m": "Distance (m)",
    "duration_seconds": "Duration (s)",
    "validity_days": "Validity (days)",
    "bill_amount": "Bill Amount",
    "discount_applied": "Discount Applied",
    "discount_value": "Discount Value",
    "min_order_amount": "Min Order Amount",
    "action_type": "Action Type",
    "action_ref": "Action Ref",
    "event_type": "Event Type",
}


def humanise(name: str) -> str:
    """Turns ``kyc_status`` into ``KYC Status``."""
    if name in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[name]
    return name.replace("_", " ").title()


@dataclass
class ColumnMeta:
    """One column of a model, as the panel needs to understand it."""

    name: str
    label: str
    kind: str
    nullable: bool = True
    primary_key: bool = False
    fk_table: Optional[str] = None
    choices: Optional[List[str]] = None
    required: bool = False
    in_form: bool = True
    secret: bool = False
    multiline: bool = False

    @property
    def widget(self) -> str:
        if self.choices or self.fk_table:
            return "select"
        if self.kind == KIND_BOOLEAN:
            return "checkbox"
        if self.kind == KIND_DATETIME:
            return "datetime"
        if self.kind == KIND_JSON or self.multiline:
            return "textarea"
        return "input"

    @property
    def input_type(self) -> str:
        return "number" if self.kind in (KIND_INTEGER, KIND_NUMBER) else "text"

    @property
    def step(self) -> str:
        return "1" if self.kind == KIND_INTEGER else "any"


@dataclass
class ModelMeta:
    """Everything the panel needs to render and mutate one table."""

    key: str
    model: Any
    label: str
    singular: str
    group: str
    columns: List[ColumnMeta] = field(default_factory=list)
    list_columns: List[str] = field(default_factory=list)
    search_columns: List[str] = field(default_factory=list)
    sort_column: str = "id"
    sort_desc: bool = True
    page_size: int = 25
    label_column: Optional[str] = None

    def column(self, name: str) -> Optional[ColumnMeta]:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    @property
    def pk(self) -> ColumnMeta:
        for col in self.columns:
            if col.primary_key:
                return col
        raise RuntimeError(f"{self.key} has no primary key")

    @property
    def form_columns(self) -> List[ColumnMeta]:
        return [col for col in self.columns if col.in_form and not col.secret]

    @property
    def list_column_metas(self) -> List[ColumnMeta]:
        metas = [self.column(name) for name in self.list_columns]
        return [col for col in metas if col is not None]

    @property
    def fk_columns(self) -> List[ColumnMeta]:
        return [col for col in self.columns if col.fk_table]


def _kind_of(column) -> str:
    column_type = column.type
    if isinstance(column_type, Boolean):
        return KIND_BOOLEAN
    if isinstance(column_type, PGUUID):
        return KIND_UUID
    if isinstance(column_type, DateTime):
        return KIND_DATETIME
    if isinstance(column_type, JSON):
        return KIND_JSON
    if isinstance(column_type, Integer):
        return KIND_INTEGER
    if isinstance(column_type, (Float, Numeric)):
        return KIND_NUMBER
    if isinstance(column_type, (Text, String)):
        return KIND_TEXT
    return KIND_TEXT


def _fk_table(column) -> Optional[str]:
    for fk in column.foreign_keys:
        return fk.target_fullname.split(".")[0]
    return None


def _build_column(column, cfg: Dict[str, Any]) -> ColumnMeta:
    name = column.name
    secret = name in set(cfg.get("secret") or ())
    choices = (cfg.get("choices") or {}).get(name)
    kind = _kind_of(column)
    multiline = kind == KIND_TEXT and getattr(column.type, "length", None) is None
    required = bool(
        not column.nullable
        and column.default is None
        and not column.primary_key
        and not secret
    )
    in_form = (
        not column.primary_key
        and not secret
        and name not in set(cfg.get("readonly") or ())
    )
    return ColumnMeta(
        name=name,
        label=humanise(name),
        kind=kind,
        nullable=bool(column.nullable),
        primary_key=bool(column.primary_key),
        fk_table=_fk_table(column),
        choices=list(choices) if choices else None,
        required=required,
        in_form=in_form,
        secret=secret,
        multiline=multiline,
    )


def build_model_meta(cfg: Dict[str, Any]) -> ModelMeta:
    """Infers a full :class:`ModelMeta` from a mapper plus its config overrides."""
    model = cfg["model"]
    columns = [_build_column(column, cfg) for column in sa_inspect(model).columns]
    by_name = {col.name: col for col in columns}

    list_columns = list(cfg.get("list_columns") or ())
    if not list_columns:
        list_columns = [
            col.name for col in columns if not col.secret and not col.primary_key
        ][:6]

    search_columns = list(cfg.get("search_columns") or ())
    if not search_columns:
        search_columns = [
            col.name
            for col in columns
            if col.kind in (KIND_TEXT, KIND_UUID)
            and not col.secret
            and not col.primary_key
        ]

    pk_name = next(col.name for col in columns if col.primary_key)
    sort_column = cfg.get("sort_column") or ("created_at" if "created_at" in by_name else pk_name)

    return ModelMeta(
        key=cfg["key"],
        model=model,
        label=cfg.get("label") or cfg["key"].replace("_", " ").title(),
        singular=cfg.get("singular") or cfg.get("label") or cfg["key"].title(),
        group=cfg.get("group") or "Other",
        columns=columns,
        list_columns=list_columns,
        search_columns=search_columns,
        sort_column=sort_column,
        sort_desc=bool(cfg.get("sort_desc", True)),
        page_size=int(cfg.get("page_size") or 25),
        label_column=cfg.get("label_column"),
    )


REGISTRY: Dict[str, ModelMeta] = {}
REGISTRY_BY_TABLE: Dict[str, ModelMeta] = {}
NAV_GROUPS: "Dict[str, List[ModelMeta]]" = {}

for _cfg in MODEL_CONFIGS:
    _meta = build_model_meta(_cfg)
    REGISTRY[_meta.key] = _meta
    REGISTRY_BY_TABLE[_meta.model.__tablename__] = _meta
    NAV_GROUPS.setdefault(_meta.group, []).append(_meta)

ALL_MODELS: List[ModelMeta] = list(REGISTRY.values())


def get_meta(key: str) -> Optional[ModelMeta]:
    return REGISTRY.get(key)


def nav_groups() -> List[Dict[str, Any]]:
    return [{"name": name, "models": metas} for name, metas in NAV_GROUPS.items()]
