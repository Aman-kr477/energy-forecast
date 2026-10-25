"""
app/api/routes/forecast.py
===========================
GET /api/forecast?delivery_date=YYYY-MM-DD&cutoff=HH:MM
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.schemas.responses import (
    ErrorBand,
    ForecastResponse,
    ForecastSlot,
    ForecastSummary,
)
from app.services.forecast_selector import (
    select_forecast_at_cutoff,
    select_forecast_at_horizon,
)
from app.services.metrics import error_band_from_history
from app.utils import data_loader
from app.utils.time_utils import london_time_to_utc

router = APIRouter()

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _parse_cutoff(delivery_date: date, cutoff_str: str):
    """Parse cutoff HH:MM as Europe/London time on the decision day (delivery_date - 1 day)."""
    if not _TIME_RE.match(cutoff_str):
        raise HTTPException(status_code=422, detail="cutoff must be HH:MM, e.g. '09:00'")
    decision_date = delivery_date - timedelta(days=1)
    try:
        return london_time_to_utc(str(decision_date), cutoff_str)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid cutoff: {exc}") from exc


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    delivery_date: date = Query(..., description="Delivery date (YYYY-MM-DD)"),
    cutoff: str = Query("09:00", description="Decision cutoff in Europe/London time (HH:MM)"),
) -> ForecastResponse:
    """
    Return the latest-at-cutoff forecast for every 30-min slot of delivery_date,
    together with actuals (if available) and a historical error band.
    """
    cutoff_utc = _parse_cutoff(delivery_date, cutoff)
    delivery_str = str(delivery_date)

    # --- Select forecasts ---
    slots_df = select_forecast_at_cutoff(
        data_loader.forecasts, delivery_str, cutoff_utc
    )

    # --- Join actuals ---
    act = data_loader.actuals
    act_day = act[act["start_time"].dt.date == delivery_date].set_index("start_time")

    # --- Error band: use only delivery days BEFORE this one (no leakage) ---
    # Find the median horizon used for this delivery day
    median_horizon = float(slots_df["horizon_hours"].median()) if slots_df["horizon_hours"].notna().any() else None

    error_band = ErrorBand(p10_mw=None, p90_mw=None, based_on_days=0)
    if median_horizon is not None:
        prior_end = pd.Timestamp(delivery_date, tz="UTC")
        prior_start = data_loader.actuals["start_time"].min()
        if prior_start < prior_end:
            prior_fct = select_forecast_at_horizon(
                data_loader.forecasts,
                prior_start,
                prior_end,
                horizon_hours=median_horizon,
            )
            prior_act = data_loader.actuals[
                (data_loader.actuals["start_time"] >= prior_start)
                & (data_loader.actuals["start_time"] < prior_end)
            ].set_index("start_time")

            if not prior_fct.empty and not prior_act.empty:
                merged = prior_fct.set_index("start_time").join(
                    prior_act[["generation"]].rename(columns={"generation": "actual_mw"}),
                    how="inner",
                )
                p10, p90 = error_band_from_history(merged.rename(columns={"forecast_mw": "forecast_mw"}))
                n_days = prior_fct["start_time"].dt.date.nunique()
                error_band = ErrorBand(p10_mw=p10, p90_mw=p90, based_on_days=n_days)

    # --- Build slot list ---
    slot_list: list[ForecastSlot] = []
    for row in slots_df.itertuples():
        st = row.start_time
        fmw = None if pd.isna(row.forecast_mw) else float(row.forecast_mw)
        pub = None if pd.isna(row.publish_time) else row.publish_time.isoformat()
        hor = None if pd.isna(row.horizon_hours) else float(row.horizon_hours)

        actual_mw = None
        error_mw = None
        if st in act_day.index:
            actual_mw = float(act_day.loc[st, "generation"])
            if fmw is not None:
                error_mw = fmw - actual_mw

        slot_list.append(
            ForecastSlot(
                start_time=st.isoformat(),
                forecast_mw=fmw,
                publish_time=pub,
                horizon_hours=hor,
                actual_mw=actual_mw,
                error_mw=error_mw,
            )
        )

    # --- Summary ---
    valid = slots_df.dropna(subset=["forecast_mw"])
    if valid.empty:
        summary = ForecastSummary()
    else:
        peak_row = valid.loc[valid["forecast_mw"].idxmax()]
        min_row = valid.loc[valid["forecast_mw"].idxmin()]
        total_mwh = float(valid["forecast_mw"].sum() * 0.5)  # 30-min periods → MWh
        pub_times = valid["publish_time"].dropna()
        summary = ForecastSummary(
            total_forecast_mwh=round(total_mwh, 1),
            peak_forecast_mw=float(peak_row["forecast_mw"]),
            peak_forecast_time=peak_row["start_time"].isoformat(),
            min_forecast_mw=float(min_row["forecast_mw"]),
            min_forecast_time=min_row["start_time"].isoformat(),
            earliest_publish_time=pub_times.min().isoformat() if not pub_times.empty else None,
            latest_publish_time=pub_times.max().isoformat() if not pub_times.empty else None,
        )

    return ForecastResponse(
        delivery_date=delivery_str,
        cutoff=cutoff_utc.isoformat(),
        slots=slot_list,
        summary=summary,
        error_band=error_band,
    )

