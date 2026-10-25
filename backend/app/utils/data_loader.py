from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)

# backend/app/utils/data_loader.py -> .parent x3 -> backend/ -> data/
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

actuals: pd.DataFrame = pd.DataFrame()
forecasts: pd.DataFrame = pd.DataFrame()


def load() -> None:
    global actuals, forecasts
    actuals_path = DATA_DIR / "actuals.parquet"
    forecasts_path = DATA_DIR / "forecasts.parquet"
    log.info("DATA_DIR resolved to: %s", DATA_DIR)
    if not actuals_path.exists():
        raise FileNotFoundError(f"Actuals not found at {actuals_path}. Run scripts/ingest.py first.")
    if not forecasts_path.exists():
        raise FileNotFoundError(f"Forecasts not found at {forecasts_path}. Run scripts/ingest.py first.")
    actuals = pd.read_parquet(actuals_path)
    forecasts = pd.read_parquet(forecasts_path)
    actuals["start_time"] = pd.to_datetime(actuals["start_time"], utc=True)
    forecasts["start_time"] = pd.to_datetime(forecasts["start_time"], utc=True)
    forecasts["publish_time"] = pd.to_datetime(forecasts["publish_time"], utc=True)
    log.info("Loaded: %d actuals, %d forecasts", len(actuals), len(forecasts))
