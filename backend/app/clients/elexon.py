"""
Elexon BMRS API client.

Handles retries, chunked date windows, and raw JSON fetching.
Never called at request time – used only by the ingest script.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

# Elexon stream endpoints return plain JSON arrays – no pagination tokens.
# We chunk by day to stay well within any undocumented size limits.


def _dt_iso(dt: datetime) -> str:
    """Format a UTC datetime as an ISO-8601 Z string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _get(url: str, params: dict[str, Any]) -> list[dict]:
    """Single GET with retries; returns parsed JSON list."""
    with httpx.Client(timeout=60.0) as client:
        log.debug("GET %s params=%s", url, params)
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected response type: {type(data)}")
        return data


def fetch_fuelhh_wind(
    publish_from: datetime,
    publish_to: datetime,
) -> list[dict]:
    """
    Fetch FUELHH wind actuals between two UTC publish datetimes.

    Parameters
    ----------
    publish_from : datetime  UTC start of publish window (inclusive)
    publish_to   : datetime  UTC end of publish window (exclusive)
    """
    url = f"{BASE_URL}/FUELHH/stream"
    params = {
        "publishDateTimeFrom": _dt_iso(publish_from),
        "publishDateTimeTo": _dt_iso(publish_to),
        "fuelType": "WIND",
    }
    return _get(url, params)


def fetch_windfor(
    publish_from: datetime,
    publish_to: datetime,
    settlement_date_from: date | None = None,
    settlement_date_to: date | None = None,
) -> list[dict]:
    """
    Fetch WINDFOR forecasts between two UTC publish datetimes.

    Optionally restrict to settlement (delivery) dates.
    """
    url = f"{BASE_URL}/WINDFOR/stream"
    params: dict[str, Any] = {
        "publishDateTimeFrom": _dt_iso(publish_from),
        "publishDateTimeTo": _dt_iso(publish_to),
    }
    if settlement_date_from:
        params["settlementDateFrom"] = settlement_date_from.isoformat()
    if settlement_date_to:
        params["settlementDateTo"] = settlement_date_to.isoformat()
    return _get(url, params)


def chunked_date_windows(
    start: datetime, end: datetime, chunk_days: int = 1
) -> list[tuple[datetime, datetime]]:
    """
    Split [start, end) into sub-windows of at most chunk_days each.

    Returns a list of (window_start, window_end) tuples.
    """
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    delta = timedelta(days=chunk_days)
    while cursor < end:
        window_end = min(cursor + delta, end)
        windows.append((cursor, window_end))
        cursor = window_end
    return windows
