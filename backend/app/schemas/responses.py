"""
app/schemas/responses.py
=========================
Pydantic response models for all API endpoints.
All timestamps are returned as ISO-8601 strings (UTC).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"


# ---------------------------------------------------------------------------
# /api/meta
# ---------------------------------------------------------------------------

class MetaResponse(BaseModel):
    delivery_dates: list[str] = Field(
        description="Available delivery dates (YYYY-MM-DD) in ascending order"
    )
    available_horizons: list[float] = Field(
        description="Distinct horizon values (hours) present in the forecast data"
    )
    default_cutoff: str = Field(
        description="Default decision cutoff as a local time string, e.g. '09:00'"
    )
    timezone: str = Field(default="Europe/London")


# ---------------------------------------------------------------------------
# /api/actuals
# ---------------------------------------------------------------------------

class ActualPoint(BaseModel):
    start_time: str
    generation_mw: float


class ActualsResponse(BaseModel):
    data: list[ActualPoint]


# ---------------------------------------------------------------------------
# /api/forecast
# ---------------------------------------------------------------------------

class ForecastSlot(BaseModel):
    start_time: str
    forecast_mw: Optional[float] = None
    publish_time: Optional[str] = None
    horizon_hours: Optional[float] = None
    actual_mw: Optional[float] = None
    error_mw: Optional[float] = Field(
        default=None,
        description="forecast_mw - actual_mw (positive = over-forecast)"
    )


class ForecastSummary(BaseModel):
    total_forecast_mwh: Optional[float] = None
    peak_forecast_mw: Optional[float] = None
    peak_forecast_time: Optional[str] = None
    min_forecast_mw: Optional[float] = None
    min_forecast_time: Optional[str] = None
    earliest_publish_time: Optional[str] = None
    latest_publish_time: Optional[str] = None


class ErrorBand(BaseModel):
    p10_mw: Optional[float] = Field(
        default=None,
        description="P10 of historical signed error at this horizon (MW)"
    )
    p90_mw: Optional[float] = Field(
        default=None,
        description="P90 of historical signed error at this horizon (MW)"
    )
    based_on_days: int = Field(
        default=0,
        description="Number of prior delivery days used to compute the band"
    )


class ForecastResponse(BaseModel):
    delivery_date: str
    cutoff: str
    slots: list[ForecastSlot]
    summary: ForecastSummary
    error_band: ErrorBand


# ---------------------------------------------------------------------------
# /api/metrics
# ---------------------------------------------------------------------------

class TimeSeriesPoint(BaseModel):
    start_time: str
    actual_mw: Optional[float] = None
    forecast_mw: Optional[float] = None
    error_mw: Optional[float] = None


class MetricsResponse(BaseModel):
    mae: float
    rmse: float
    bias: float
    p90_abs_error: float
    normalised_mae: float
    sample_count: int
    horizon_hours: float
    time_series: list[TimeSeriesPoint]


# ---------------------------------------------------------------------------
# /api/metrics/by-horizon
# ---------------------------------------------------------------------------

class HorizonMetric(BaseModel):
    horizon_hours: float
    mae: float
    rmse: float
    bias: float
    sample_count: int


class MetricsByHorizonResponse(BaseModel):
    data: list[HorizonMetric]


# ---------------------------------------------------------------------------
# /api/metrics/error-distribution
# ---------------------------------------------------------------------------

class HistogramBinOut(BaseModel):
    bin_left: float
    bin_right: float
    count: int


class ErrorDistributionResponse(BaseModel):
    horizon_hours: float
    bins: list[HistogramBinOut]
    sample_count: int
