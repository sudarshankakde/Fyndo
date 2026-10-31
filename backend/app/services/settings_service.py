"""Read/write access to the Super Admin's platform-wide settings."""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_settings import (
    AUTO_APPROVE_KYC,
    AUTO_APPROVE_REELS,
    AUTO_TRIAL_DURATION_DAYS,
    AUTO_TRIAL_ENABLED,
    MAINTENANCE_MODE,
    SETTING_DEFAULTS,
    SystemSetting,
)


async def get_setting(db: AsyncSession, key: str) -> Any:
    row = await db.get(SystemSetting, key)
    if row is not None:
        return row.value
    return SETTING_DEFAULTS.get(key, {}).get("value")


async def set_setting(
    db: AsyncSession, key: str, value: Any, *, updated_by: Optional[uuid.UUID] = None
) -> SystemSetting:
    if key not in SETTING_DEFAULTS:
        raise KeyError(key)
    row = await db.get(SystemSetting, key)
    if row is None:
        row = SystemSetting(key=key, description=SETTING_DEFAULTS[key]["description"])
        db.add(row)
    if key in (AUTO_APPROVE_REELS, AUTO_APPROVE_KYC, AUTO_TRIAL_ENABLED, MAINTENANCE_MODE) and isinstance(value, str):
        row.value = value.strip().lower() in ("true", "1", "yes", "on", "t")
    elif key == AUTO_TRIAL_DURATION_DAYS:
        try:
            row.value = max(1, min(3650, int(value)))
        except (ValueError, TypeError):
            row.value = 90
    else:
        row.value = value
    row.updated_by_user_id = updated_by
    await db.flush()
    return row


async def list_settings(db: AsyncSession) -> List[Dict[str, Any]]:
    stored = {
        row.key: row
        for row in (await db.execute(select(SystemSetting))).scalars().all()
    }
    items = []
    for key, default in SETTING_DEFAULTS.items():
        row = stored.get(key)
        items.append({
            "key": key,
            "value": row.value if row else default["value"],
            "description": default["description"],
            "updated_at": row.updated_at if row else None,
        })
    return items


async def is_auto_approve_enabled(db: AsyncSession) -> bool:
    val = await get_setting(db, AUTO_APPROVE_REELS)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on", "t")
    return bool(val)


async def is_auto_approve_kyc_enabled(db: AsyncSession) -> bool:
    val = await get_setting(db, AUTO_APPROVE_KYC)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on", "t")
    return bool(val)


async def is_auto_trial_enabled(db: AsyncSession) -> bool:
    val = await get_setting(db, AUTO_TRIAL_ENABLED)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on", "t")
    return True if val is None else bool(val)


async def get_auto_trial_duration_days(db: AsyncSession) -> int:
    val = await get_setting(db, AUTO_TRIAL_DURATION_DAYS)
    try:
        days = int(val)
        return max(1, min(3650, days))
    except (ValueError, TypeError):
        return 90


async def is_maintenance_mode_enabled(db: AsyncSession) -> bool:
    val = await get_setting(db, MAINTENANCE_MODE)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on", "t")
    return bool(val)
