"""
app/services/forecast_selector.py
==================================
Pure functions for selecting the correct forecast at a given cutoff time
and for computing horizon-based forecasts.

No web or I/O imports – all functions accept DataFrames and return DataFrames
or scalars so they can be tested independently of the web layer.

Definitions (from spec)
-----------------------
- Cutoff          : UTC datetime at which a purchase decision is made.
- Latest forecast : for each 30-min delivery slot, the row in the forecasts
                    DataFrame with the greatest publish_time that is <= cutoff.
                    Returns null for a slot when no eligible row exists.
- Horizon (hours) : (start_time - publish_time).total_seconds() / 3600
- Forecast at H   : for each slot, the latest forecast published at least
                    H hours before start_time  (publish_time <= start_time - H hours).
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def select_forecast_at_cutoff(
    forecasts: pd.DataFrame,
    delivery_date: str,
    cutoff: datetime,
) -> pd.DataFrame:
    """
    Return the latest eligible forecast for every 30-min slot of a delivery day.

    Parameters
    ----------
    forecasts     : DataFrame with columns [start_time, publish_time, generation]
                    start_time and publish_time must be tz-aware UTC.
    delivery_date : ISO date string, e.g. "2026-01-02"
    cutoff        : tz-aware UTC datetime. Only forecasts with
                    publish_time <= cutoff are eligible.

    Returns
    -------
    DataFrame with columns:
        start_time      datetime64[UTC]
        forecast_mw     float   (NaN where no eligible forecast exists)
        publish_time    datetime64[UTC]  (NaT where no eligible forecast)
        horizon_hours   float   (NaN where no eligible forecast)

    The returned DataFrame has exactly 48 rows (one per 30-min slot of the day),
    sorted by start_time.
    """
    # Build the full 48-slot spine for the delivery day
    day = pd.Timestamp(delivery_date, tz="UTC")
    spine = pd.DataFrame(
        {"start_time": pd.date_range(day, periods=48, freq="30min", tz="UTC")}
    )

    # Filter forecast table to this delivery day and to eligible publish times
    day_fct = forecasts[
        (forecasts["start_time"].dt.date == day.date())
        & (forecasts["publish_time"] <= cutoff)
    ].copy()

    if day_fct.empty:
        spine["forecast_mw"] = float("nan")
        spine["publish_time"] = pd.NaT
        spine["horizon_hours"] = float("nan")
        return spine

    # For each slot, pick the row with the greatest eligible publish_time
    latest = (
        day_fct.sort_values("publish_time")
        .groupby("start_time", as_index=False)
        .last()
        .rename(columns={"generation": "forecast_mw"})
    )

    # Merge onto the spine so missing slots become NaN/NaT
    result = spine.merge(latest[["start_time", "forecast_mw", "publish_time"]], on="start_time", how="left")

    # Compute horizon where we have a publish_time
    mask = result["publish_time"].notna()
    result["horizon_hours"] = float("nan")
    result.loc[mask, "horizon_hours"] = (
        (result.loc[mask, "start_time"] - result.loc[mask, "publish_time"])
        .dt.total_seconds()
        / 3600
    )

    return result.sort_values("start_time").reset_index(drop=True)


def select_forecast_at_horizon(
    forecasts: pd.DataFrame,
    start: datetime,
    end: datetime,
    horizon_hours: float,
) -> pd.DataFrame:
    """
    For each 30-min slot in [start, end), return the latest forecast
    published at least `horizon_hours` before that slot's start_time.

    This is used for the accuracy screen to evaluate forecast skill at a
    consistent look-ahead distance.

    Parameters
    ----------
    forecasts      : DataFrame with columns [start_time, publish_time, generation]
    start          : tz-aware UTC datetime (inclusive)
    end            : tz-aware UTC datetime (exclusive)
    horizon_hours  : minimum hours before start_time for the forecast to qualify

    Returns
    -------
    DataFrame with columns:
        start_time      datetime64[UTC]
        forecast_mw     float   (NaN where no eligible forecast exists)
        publish_time    datetime64[UTC]  (NaT where none)
        horizon_hours   float
    """
    slots = forecasts[
        (forecasts["start_time"] >= start) & (forecasts["start_time"] < end)
    ].copy()

    if slots.empty:
        return pd.DataFrame(
            columns=["start_time", "forecast_mw", "publish_time", "horizon_hours"]
        )

    # Eligibility: publish_time <= start_time - horizon_hours
    delta = pd.Timedelta(hours=horizon_hours)
    eligible = slots[slots["publish_time"] <= slots["start_time"] - delta].copy()

    if eligible.empty:
        # Return spine with NaNs
        spine_times = slots["start_time"].unique()
        return pd.DataFrame({
            "start_time": sorted(spine_times),
            "forecast_mw": float("nan"),
            "publish_time": pd.NaT,
            "horizon_hours": float("nan"),
        })

    latest = (
        eligible.sort_values("publish_time")
        .groupby("start_time", as_index=False)
        .last()
        .rename(columns={"generation": "forecast_mw"})
    )
    latest["horizon_hours"] = (
        (latest["start_time"] - latest["publish_time"]).dt.total_seconds() / 3600
    )

    # Re-attach spine to surface slots with no eligible forecast
    all_slots = pd.DataFrame({"start_time": sorted(slots["start_time"].unique())})
    result = all_slots.merge(
        latest[["start_time", "forecast_mw", "publish_time", "horizon_hours"]],
        on="start_time",
        how="left",
    )
    return result.reset_index(drop=True)
