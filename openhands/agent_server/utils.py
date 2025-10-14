from datetime import UTC, datetime


def utc_now():
    """Return the current time in UTC format (Since datetime.utcnow is deprecated)"""
    return datetime.now(UTC)


def normalize_datetime_to_server_timezone(dt: datetime) -> datetime:
    """
    Normalize datetime to server timezone for consistent comparison.

    If the datetime has timezone info, convert to server timezone.
    If it's naive (no timezone), assume it's already in server timezone.

    Args:
        dt: Input datetime (may be timezone-aware or naive)

    Returns:
        Datetime in server timezone (naive)
    """
    if dt.tzinfo is not None:
        # Timezone-aware: convert to server timezone
        server_tz = datetime.now().astimezone().tzinfo
        return dt.astimezone(server_tz).replace(tzinfo=None)
    else:
        # Naive datetime: assume it's already in server timezone
        return dt
