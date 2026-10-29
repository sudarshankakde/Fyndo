from datetime import datetime, timedelta, timezone

# Indian Standard Time (IST) is UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def ist_now() -> datetime:
    """Returns the current datetime in Indian Standard Time (IST, UTC+5:30)."""
    return datetime.now(IST)


def to_ist(dt: datetime) -> datetime:
    """Ensures a datetime object is localized to Indian Standard Time (IST)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)

