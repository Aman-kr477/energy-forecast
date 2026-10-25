"""
scripts/ingest.py
=================
One-shot script to pull January 2026 wind data from Elexon BMRS and
save cleaned Parquet snapshots under backend/data/.

Run from the backend/ directory:
    python scripts/ingest.py

Outputs
-------
data/actuals.parquet   – 30-min wind actuals (FUELHH, fuelType=WIND)
data/forecasts.parquet – hourly wind forecasts (WINDFOR), upsampled to 30-min

Both files store timestamps as UTC. Columns and dtypes are documented below.
"""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# Allow running as  python scripts/ingest.py  from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.elexon import (
    chunked_date_windows,
    fetch_fuelhh_wind,
    fetch_windfor,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------
# Decisions for delivery days 2 Jan – 1 Feb 2026 are made on
# 1 Jan – 31 Jan 2026 at some cutoff (default 09:00 London = 09:00 UTC in Jan).
# We pull:
#   Actuals  : startTime covers 2 Jan 00:00Z – 2 Feb 00:00Z  (delivery days)
#   Forecasts: publishTime covers 1 Jan 00:00Z – 31 Jan 09:00Z (decision days)
#              with startTime (delivery) covering 2 Jan – 1 Feb

DELIVERY_START = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
DELIVERY_END = datetime(2026, 2, 2, 0, 0, tzinfo=timezone.utc)   # exclusive

# Actuals: published ~30 min after each period ends, so we extend slightly
ACTUALS_PUB_FROM = datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc)
ACTUALS_PUB_TO = datetime(2026, 2, 2, 1, 0, tzinfo=timezone.utc)

# Forecasts: all forecasts published any time on decision days (Jan 1–31)
FORECAST_PUB_FROM = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
FORECAST_PUB_TO = datetime(2026, 1, 31, 23, 59, tzinfo=timezone.utc)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


# ---------------------------------------------------------------------------
# Actuals ingestion
# ---------------------------------------------------------------------------

def ingest_actuals() -> pd.DataFrame:
    """
    Pull FUELHH WIND actuals, deduplicate, validate, and return a clean DataFrame.

    Schema
    ------
    start_time   : datetime64[ns, UTC]  – start of the 30-min settlement period
    generation   : float64              – MW
    """
    log.info("=== Ingesting actuals (FUELHH WIND) ===")
    windows = chunked_date_windows(ACTUALS_PUB_FROM, ACTUALS_PUB_TO, chunk_days=1)
    log.info("Fetching in %d daily chunks", len(windows))

    rows: list[dict] = []
    for i, (pub_from, pub_to) in enumerate(windows, 1):
        chunk = fetch_fuelhh_wind(pub_from, pub_to)
        log.info("  Chunk %d/%d: %d rows", i, len(windows), len(chunk))
        rows.extend(chunk)

    log.info("Raw rows fetched: %d", len(rows))

    if not rows:
        raise RuntimeError("No actuals data returned – check date range and API.")

    df = pd.DataFrame(rows)

    # Parse and localise timestamps
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["generation"] = df["generation"].astype(float)

    # Keep only delivery window
    df = df[(df["start_time"] >= DELIVERY_START) & (df["start_time"] < DELIVERY_END)]
    log.info("Rows after delivery-window filter: %d", len(df))

    # Deduplicate: if a period appears twice, keep the later publish
    df = df.sort_values("publishTime")
    before = len(df)
    df = df.drop_duplicates(subset=["start_time"], keep="last")
    log.info("Duplicates dropped: %d  →  %d rows", before, len(df))

    df = df[["start_time", "generation"]].sort_values("start_time").reset_index(drop=True)

    # Validate: expect 48 periods per day
    n_days = (DELIVERY_END - DELIVERY_START).days
    expected = n_days * 48
    actual = len(df)
    log.info("Expected rows: %d   Actual: %d", expected, actual)
    if actual < expected:
        missing = expected - actual
        log.warning("⚠  %d missing 30-min slots in actuals", missing)
        _log_gaps(df, "start_time", timedelta(minutes=30))
    else:
        log.info("✓  No gaps detected in actuals")

    return df


def _log_gaps(df: pd.DataFrame, col: str, expected_step: timedelta) -> None:
    """Log any gaps larger than expected_step."""
    times = df[col].sort_values().reset_index(drop=True)
    diffs = times.diff().dropna()
    gaps = diffs[diffs > expected_step]
    for idx in gaps.index:
        log.warning("  Gap after %s  (delta=%s)", times[idx - 1], diffs[idx])


# ---------------------------------------------------------------------------
# Forecasts ingestion
# ---------------------------------------------------------------------------

def ingest_forecasts() -> pd.DataFrame:
    """
    Pull WINDFOR forecasts, deduplicate, upsample to 30-min, and return a clean DataFrame.

    WINDFOR resolution is 60-min. We upsample to 30-min by repeating each
    hourly value for both half-hour slots it covers:
        startTime 00:00 → slots 00:00 and 00:30
        startTime 01:00 → slots 01:00 and 01:30  …etc.

    This is conservative and standard practice in GB energy forecasting.

    Schema
    ------
    start_time   : datetime64[ns, UTC]  – start of the 30-min slot (delivery)
    publish_time : datetime64[ns, UTC]  – when this forecast was published
    generation   : float64              – forecast MW
    """
    log.info("=== Ingesting forecasts (WINDFOR) ===")

    # Fetch in daily publish-time chunks; filter to delivery window server-side
    windows = chunked_date_windows(FORECAST_PUB_FROM, FORECAST_PUB_TO, chunk_days=1)
    log.info("Fetching in %d daily chunks", len(windows))

    rows: list[dict] = []
    for i, (pub_from, pub_to) in enumerate(windows, 1):
        chunk = fetch_windfor(
            pub_from,
            pub_to,
            settlement_date_from=date(2026, 1, 2),
            settlement_date_to=date(2026, 2, 1),
        )
        log.info("  Chunk %d/%d: %d rows", i, len(windows), len(chunk))
        rows.extend(chunk)

    log.info("Raw rows fetched: %d", len(rows))

    if not rows:
        raise RuntimeError("No forecast data returned – check date range and API.")

    df = pd.DataFrame(rows)

    df["start_time_hourly"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = df["generation"].astype(float)

    # Keep only target delivery window
    df = df[
        (df["start_time_hourly"] >= DELIVERY_START)
        & (df["start_time_hourly"] < DELIVERY_END)
    ]
    log.info("Rows after delivery-window filter: %d", len(df))

    # Deduplicate: for the same (startTime, publishTime) keep one row
    before = len(df)
    df = df.drop_duplicates(subset=["start_time_hourly", "publish_time"], keep="last")
    log.info("Duplicates dropped: %d  →  %d rows", before, len(df))

    # -------------------------------------------------------------------
    # Upsample 60-min → 30-min
    # Each hourly row spawns two rows: one at hh:00 and one at hh:30
    # The forecast MW value is identical for both half-hours.
    # -------------------------------------------------------------------
    log.info("Upsampling 60-min WINDFOR to 30-min …")
    half_hour = timedelta(minutes=30)

    base = df[["start_time_hourly", "publish_time", "generation"]].copy()
    plus30 = base.copy()
    plus30["start_time_hourly"] = plus30["start_time_hourly"] + half_hour

    # Filter the +30 rows to stay within delivery window
    plus30 = plus30[plus30["start_time_hourly"] < DELIVERY_END]

    combined = pd.concat([base, plus30], ignore_index=True)
    combined = combined.rename(columns={"start_time_hourly": "start_time"})
    combined = combined.sort_values(["start_time", "publish_time"]).reset_index(drop=True)

    log.info("Rows after upsampling: %d", len(combined))

    # Validate coverage
    n_days = (DELIVERY_END - DELIVERY_START).days
    expected_slots = n_days * 48
    actual_slots = combined["start_time"].nunique()
    log.info("Distinct 30-min slots covered: %d / %d", actual_slots, expected_slots)
    if actual_slots < expected_slots:
        log.warning("⚠  Some delivery slots have no forecast rows")

    return combined[["start_time", "publish_time", "generation"]]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- Actuals ---
    actuals = ingest_actuals()
    out_actuals = DATA_DIR / "actuals.parquet"
    actuals.to_parquet(out_actuals, index=False)
    log.info("Saved actuals → %s  (%d rows)", out_actuals, len(actuals))

    # --- Forecasts ---
    forecasts = ingest_forecasts()
    out_forecasts = DATA_DIR / "forecasts.parquet"
    forecasts.to_parquet(out_forecasts, index=False)
    log.info("Saved forecasts → %s  (%d rows)", out_forecasts, len(forecasts))

    # --- Summary ---
    log.info("")
    log.info("=== Ingestion complete ===")
    log.info("Actuals  : %d rows, %s to %s",
             len(actuals),
             actuals["start_time"].min(),
             actuals["start_time"].max())
    log.info("Forecasts: %d rows, publish %s to %s",
             len(forecasts),
             forecasts["publish_time"].min(),
             forecasts["publish_time"].max())


if __name__ == "__main__":
    main()
