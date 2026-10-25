"""
app/utils/time_utils.py
========================
Timezone conversion helpers.
All data is stored and computed in UTC; this module converts to/from
Europe/London for display and input parsing.
"""
from __future__ import annotations

from datetime import datetime, time, timezone

import pytz

LONDON = pytz.timezone("Europe/London")
DEFAULT_CUTOFF_LOCAL = time(9, 0)   # 09:00 Europe/London


def london_time_to_utc(date_str: str, time_str: str) -> datetime:
    """
    Convert a date + local time string to a UTC datetime.

    Parameters
    ----------
    date_str : "YYYY-MM-DD"
    time_str : "HH:MM"

    Returns
    -------
    tz-aware UTC datetime
    """
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    local = LONDON.localize(naive, is_dst=None)   # raises if ambiguous
    return local.astimezone(pytz.utc)


def utc_to_london_str(dt: datetime) -> str:
    """Format a UTC datetime as an ISO-8601 string in Europe/London."""
    if dt is None:
        return ""
    utc_dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    london_dt = utc_dt.astimezone(LONDON)
    return london_dt.isoformat()


def fmt_utc(dt) -> str | None:
    """Return an ISO-8601 UTC string, or None if dt is NaT/None."""
    if dt is None or (hasattr(dt, "isnull") and dt.isnull()) or str(dt) == "NaT":
        return None
    if hasattr(dt, "isoformat"):
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return None
