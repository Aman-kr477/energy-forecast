"""
app/services/metrics.py
========================
Pure functions for computing forecast accuracy metrics.

No web or I/O imports.

Definitions (from spec)
-----------------------
- Error          = forecast - actual  (positive = over-forecast)
- MAE            = mean(|error|)
- RMSE           = sqrt(mean(error^2))
- Bias           = mean(error)
- P90 abs error  = 90th percentile of |error|
- Normalised MAE = MAE / mean(actual)   [not MAPE; avoids division by near-zero]
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data classes for metric results
# ---------------------------------------------------------------------------

@dataclass
class AccuracyMetrics:
    """Scalar accuracy metrics for a given sample."""
    mae: float
    rmse: float
    bias: float
    p90_abs_error: float
    normalised_mae: float
    sample_count: int


@dataclass
class HorizonBucket:
    """Metrics for a single horizon bucket."""
    horizon_hours: float   # bucket centre (e.g. 6, 12, 18, 24 …)
    mae: float
    rmse: float
    bias: float
    sample_count: int


@dataclass
class HistogramBin:
    """One bin of the error distribution histogram."""
    bin_left: float
    bin_right: float
    count: int


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _errors(forecast_mw: pd.Series, actual_mw: pd.Series) -> pd.Series:
    """Return error series, dropping rows where either value is NaN."""
    df = pd.DataFrame({"f": forecast_mw, "a": actual_mw}).dropna()
    return df["f"] - df["a"]


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_metrics(
    forecast_mw: pd.Series,
    actual_mw: pd.Series,
) -> AccuracyMetrics:
    """
    Compute all scalar accuracy metrics from paired forecast and actual series.

    Parameters
    ----------
    forecast_mw : Series of forecast values (MW)
    actual_mw   : Series of actual values (MW), same index as forecast_mw

    Returns
    -------
    AccuracyMetrics dataclass. Raises ValueError if fewer than 2 paired rows.
    """
    errors = _errors(forecast_mw, actual_mw)
    n = len(errors)
    if n < 2:
        raise ValueError(f"Need at least 2 paired non-null rows; got {n}")

    abs_errors = errors.abs()
    mae = float(abs_errors.mean())
    rmse = float(math.sqrt((errors**2).mean()))
    bias = float(errors.mean())
    p90 = float(np.percentile(abs_errors, 90))

    # Normalised MAE: use mean actual from the same (non-null paired) rows
    paired = pd.DataFrame({"f": forecast_mw, "a": actual_mw}).dropna()
    mean_actual = float(paired["a"].mean())
    if mean_actual == 0:
        normalised_mae = float("nan")
    else:
        normalised_mae = mae / mean_actual

    return AccuracyMetrics(
        mae=mae,
        rmse=rmse,
        bias=bias,
        p90_abs_error=p90,
        normalised_mae=normalised_mae,
        sample_count=n,
    )


def compute_metrics_by_horizon(
    merged: pd.DataFrame,
    bucket_size_hours: float = 6.0,
) -> list[HorizonBucket]:
    """
    Group paired (forecast, actual, horizon_hours) rows into horizon buckets
    and compute MAE, RMSE, bias per bucket.

    Parameters
    ----------
    merged          : DataFrame with columns [forecast_mw, actual_mw, horizon_hours]
    bucket_size_hours : width of each bucket in hours (default 6)

    Returns
    -------
    List of HorizonBucket, sorted by horizon_hours ascending.
    """
    df = merged[["forecast_mw", "actual_mw", "horizon_hours"]].dropna()
    if df.empty:
        return []

    df = df.copy()
    df["bucket"] = (df["horizon_hours"] // bucket_size_hours) * bucket_size_hours + bucket_size_hours / 2

    results: list[HorizonBucket] = []
    for centre, group in df.groupby("bucket"):
        errors = group["forecast_mw"] - group["actual_mw"]
        results.append(
            HorizonBucket(
                horizon_hours=float(centre),
                mae=float(errors.abs().mean()),
                rmse=float(math.sqrt((errors**2).mean())),
                bias=float(errors.mean()),
                sample_count=len(group),
            )
        )

    return sorted(results, key=lambda b: b.horizon_hours)


def compute_error_histogram(
    forecast_mw: pd.Series,
    actual_mw: pd.Series,
    n_bins: int = 20,
) -> list[HistogramBin]:
    """
    Compute a histogram of forecast errors (forecast - actual).

    Parameters
    ----------
    forecast_mw : Series of forecast MW values
    actual_mw   : Series of actual MW values
    n_bins      : number of histogram bins (default 20)

    Returns
    -------
    List of HistogramBin sorted by bin_left.
    """
    errors = _errors(forecast_mw, actual_mw)
    if errors.empty:
        return []

    counts, edges = np.histogram(errors.values, bins=n_bins)
    return [
        HistogramBin(
            bin_left=float(edges[i]),
            bin_right=float(edges[i + 1]),
            count=int(counts[i]),
        )
        for i in range(len(counts))
    ]


def error_band_from_history(
    historical_merged: pd.DataFrame,
) -> tuple[float | None, float | None]:
    """
    Compute the P10 and P90 of absolute errors from historical data.

    Used to draw the uncertainty band on the forecast chart.
    Returns (None, None) if there are fewer than 2 rows.

    Parameters
    ----------
    historical_merged : DataFrame with columns [forecast_mw, actual_mw]
    """
    errors = _errors(historical_merged["forecast_mw"], historical_merged["actual_mw"])
    if len(errors) < 2:
        return None, None
    # signed errors for band (not abs) so we show asymmetric bands
    p10 = float(np.percentile(errors, 10))
    p90 = float(np.percentile(errors, 90))
    return p10, p90
