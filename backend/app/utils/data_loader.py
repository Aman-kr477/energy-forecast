"""
app/utils/data_loader.py
=========================
Loads the Parquet snapshots into memory once at startup.
All downstream code reads from the module-level DataFrames.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Module-level singletons – populated by load()
actuals: pd.DataFrame = pd.DataFrame()
forecasts: pd.DataFrame = pd.DataFrame()


def load() -> None:
    """
    Read actuals.parquet and forecasts.parquet into memory.
    Called once from the FastAPI lifespan hook.
    Raises FileNotFoundError if snapshots are missing.
    """
    global actuals, forecasts

    actuals_path = DATA_DIR / "actuals.parquet"
    forecasts_path = DATA_DIR / "forecasts.parquet"

    if not actuals_path.exists():
        raise FileNotFoundError(
            f"Actuals snapshot not found at {actuals_path}. "
            "Run scripts/ingest.py first."
        )
    if not forecasts_path.exists():
        raise FileNotFoundError(
            f"Forecasts snapshot not found at {forecasts_path}. "
            "Run scripts/ingest.py first."
        )

    actuals = pd.read_parquet(actuals_path)
    forecasts = pd.read_parquet(forecasts_path)

    # Ensure tz-aware UTC (parquet preserves this, but be explicit)
    actuals["start_time"] = pd.to_datetime(actuals["start_time"], utc=True)
    forecasts["start_time"] = pd.to_datetime(forecasts["start_time"], utc=True)
    forecasts["publish_time"] = pd.to_datetime(forecasts["publish_time"], utc=True)

    log.info(
        "Data loaded: %d actuals rows, %d forecast rows",
        len(actuals),
        len(forecasts),
    )
