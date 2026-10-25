"""
app/api/routes/metrics.py
==========================
GET /api/metrics?start&end&horizon
GET /api/metrics/by-horizon?start&end
GET /api/metrics/error-distribution?start&end&horizon
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.schemas.responses import (
    ErrorDistributionResponse,
    HistogramBinOut,
    HorizonMetric,
    MetricsByHorizonResponse,
    MetricsResponse,
    TimeSeriesPoint,
)
from app.services.forecast_selector import select_forecast_at_horizon
from app.services.metrics import (
    compute_error_histogram,
    compute_metrics,
    compute_metrics_by_horizon,
)
from app.utils import data_loader

router = APIRouter()


def _date_range(start: date, end: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return UTC Timestamps for an inclusive date range."""
    if end < start:
        raise HTTPException(status_code=422, detail="end must be >= start")
    return pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)


def _build_merged(
    start: date, end: date, horizon_hours: float
) -> pd.DataFrame:
    """
    Merge forecast-at-horizon with actuals for the given date range.
    Returns a DataFrame with [start_time, forecast_mw, actual_mw, horizon_hours].
    """
    start_dt, end_dt = _date_range(start, end)

    fct = select_forecast_at_horizon(
        data_loader.forecasts, start_dt, end_dt, horizon_hours
    )
    if fct.empty:
        return pd.DataFrame(columns=["start_time", "forecast_mw", "actual_mw", "horizon_hours"])

    act = data_loader.actuals
    act_range = act[(act["start_time"] >= start_dt) & (act["start_time"] < end_dt)]

    merged = fct.set_index("start_time").join(
        act_range.set_index("start_time")[["generation"]].rename(
            columns={"generation": "actual_mw"}
        ),
        how="left",
    ).reset_index()

    return merged


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end: date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    horizon: float = Query(..., description="Forecast horizon in hours (e.g. 12.0)"),
) -> MetricsResponse:
    """Scalar accuracy metrics + time series for a given horizon."""
    if horizon < 0:
        raise HTTPException(status_code=422, detail="horizon must be >= 0")

    merged = _build_merged(start, end, horizon)
    valid = merged.dropna(subset=["forecast_mw", "actual_mw"])

    if len(valid) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Fewer than 2 paired rows for horizon={horizon}h in {start}–{end}",
        )

    m = compute_metrics(valid["forecast_mw"], valid["actual_mw"])

    ts: list[TimeSeriesPoint] = []
    for row in merged.sort_values("start_time").itertuples():
        fmw = None if pd.isna(row.forecast_mw) else float(row.forecast_mw)
        amw = None if pd.isna(row.actual_mw) else float(row.actual_mw)
        err = (fmw - amw) if (fmw is not None and amw is not None) else None
        ts.append(
            TimeSeriesPoint(
                start_time=row.start_time.isoformat(),
                actual_mw=amw,
                forecast_mw=fmw,
                error_mw=err,
            )
        )

    return MetricsResponse(
        mae=m.mae,
        rmse=m.rmse,
        bias=m.bias,
        p90_abs_error=m.p90_abs_error,
        normalised_mae=m.normalised_mae,
        sample_count=m.sample_count,
        horizon_hours=horizon,
        time_series=ts,
    )


@router.get("/metrics/by-horizon", response_model=MetricsByHorizonResponse)
def get_metrics_by_horizon(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end: date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
) -> MetricsByHorizonResponse:
    """MAE, RMSE, bias bucketed by forecast horizon (6-hour buckets)."""
    start_dt, end_dt = _date_range(start, end)

    fct = data_loader.forecasts
    act = data_loader.actuals

    fct_range = fct[(fct["start_time"] >= start_dt) & (fct["start_time"] < end_dt)].copy()
    act_range = act[(act["start_time"] >= start_dt) & (act["start_time"] < end_dt)]

    if fct_range.empty or act_range.empty:
        raise HTTPException(
            status_code=404, detail=f"No data for range {start}–{end}"
        )

    # Compute horizon for every forecast row (positive = forecast published before the slot)
    fct_range["horizon_hours"] = (
        (fct_range["start_time"] - fct_range["publish_time"])
        .dt.total_seconds()
        .div(3600)
    )
    # Only keep rows where the forecast was made BEFORE the target slot
    fct_range = fct_range[fct_range["horizon_hours"] > 0]

    merged = fct_range.rename(columns={"generation": "forecast_mw"}).set_index(
        "start_time"
    ).join(
        act_range.set_index("start_time")[["generation"]].rename(
            columns={"generation": "actual_mw"}
        ),
        how="inner",
    ).reset_index()

    if merged.empty:
        raise HTTPException(status_code=404, detail="No paired data found")

    buckets = compute_metrics_by_horizon(merged, bucket_size_hours=6.0)

    return MetricsByHorizonResponse(
        data=[
            HorizonMetric(
                horizon_hours=b.horizon_hours,
                mae=b.mae,
                rmse=b.rmse,
                bias=b.bias,
                sample_count=b.sample_count,
            )
            for b in buckets
        ]
    )


@router.get("/metrics/error-distribution", response_model=ErrorDistributionResponse)
def get_error_distribution(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end: date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    horizon: float = Query(..., description="Forecast horizon in hours"),
) -> ErrorDistributionResponse:
    """Histogram of forecast errors (forecast - actual) at a given horizon."""
    if horizon < 0:
        raise HTTPException(status_code=422, detail="horizon must be >= 0")

    merged = _build_merged(start, end, horizon)
    valid = merged.dropna(subset=["forecast_mw", "actual_mw"])

    if valid.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No paired data for horizon={horizon}h in {start}–{end}",
        )

    bins = compute_error_histogram(valid["forecast_mw"], valid["actual_mw"], n_bins=20)

    return ErrorDistributionResponse(
        horizon_hours=horizon,
        bins=[
            HistogramBinOut(bin_left=b.bin_left, bin_right=b.bin_right, count=b.count)
            for b in bins
        ],
        sample_count=len(valid),
    )

