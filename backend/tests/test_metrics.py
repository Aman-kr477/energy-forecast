"""
tests/test_metrics.py
======================
Unit tests for app/services/metrics.py

Tests cover:
- MAE, RMSE, bias, P90, normalised MAE against hand-calculated values
- Error = forecast - actual (positive = over-forecast)
- Edge cases: empty input, single row, all-zero actuals
- Histogram bin counts
- Horizon bucket grouping
- error_band_from_history P10/P90
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.services.metrics import (
    AccuracyMetrics,
    compute_error_histogram,
    compute_metrics,
    compute_metrics_by_horizon,
    error_band_from_history,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _s(*values) -> pd.Series:
    return pd.Series(values, dtype=float)


# ---------------------------------------------------------------------------
# compute_metrics – hand-calculated reference cases
# ---------------------------------------------------------------------------

class TestComputeMetrics:

    def test_simple_hand_calculated(self):
        """
        forecast = [100, 200, 300, 400]
        actual   = [ 90, 210, 280, 420]
        errors   = [ 10, -10,  20, -20]

        MAE      = (10 + 10 + 20 + 20) / 4 = 15
        RMSE     = sqrt((100 + 100 + 400 + 400) / 4) = sqrt(250) ≈ 15.811
        bias     = (10 - 10 + 20 - 20) / 4 = 0
        P90      = 90th percentile of [10, 10, 20, 20] = 20
        mean_act = (90 + 210 + 280 + 420) / 4 = 250
        nMAE     = 15 / 250 = 0.06
        """
        f = _s(100, 200, 300, 400)
        a = _s(90, 210, 280, 420)
        m = compute_metrics(f, a)

        assert m.sample_count == 4
        assert abs(m.mae - 15.0) < 1e-9
        assert abs(m.rmse - math.sqrt(250)) < 1e-9
        assert abs(m.bias - 0.0) < 1e-9
        assert m.p90_abs_error == pytest.approx(20.0, abs=0.5)
        assert abs(m.normalised_mae - 0.06) < 1e-9

    def test_positive_bias(self):
        """All forecasts are too high → positive bias."""
        f = _s(200, 200, 200)
        a = _s(100, 100, 100)
        m = compute_metrics(f, a)
        assert m.bias == pytest.approx(100.0)
        assert m.mae == pytest.approx(100.0)

    def test_negative_bias(self):
        """All forecasts are too low → negative bias."""
        f = _s(100, 100, 100)
        a = _s(200, 200, 200)
        m = compute_metrics(f, a)
        assert m.bias == pytest.approx(-100.0)

    def test_perfect_forecast(self):
        """Zero error everywhere."""
        f = _s(500, 600, 700)
        a = _s(500, 600, 700)
        m = compute_metrics(f, a)
        assert m.mae == 0.0
        assert m.rmse == 0.0
        assert m.bias == 0.0
        assert m.normalised_mae == 0.0

    def test_nan_rows_are_dropped(self):
        """NaN pairs are ignored; metrics computed on remaining 3 rows."""
        f = _s(100, float("nan"), 300, 400)
        a = _s(90, 210, float("nan"), 420)
        # After dropping rows 1 and 2: errors = [10, -20], n=2
        m = compute_metrics(f, a)
        assert m.sample_count == 2
        assert m.mae == pytest.approx(15.0)

    def test_normalised_mae_nan_when_mean_actual_zero(self):
        """Mean actual == 0 → normalised_mae is NaN."""
        f = _s(10, 20)
        a = _s(0, 0)
        m = compute_metrics(f, a)
        assert math.isnan(m.normalised_mae)

    def test_raises_when_fewer_than_two_rows(self):
        """Single valid pair raises ValueError."""
        f = _s(100)
        a = _s(90)
        with pytest.raises(ValueError, match="at least 2"):
            compute_metrics(f, a)

    def test_raises_on_empty_input(self):
        """Fully NaN input raises ValueError."""
        f = _s(float("nan"), float("nan"))
        a = _s(float("nan"), float("nan"))
        with pytest.raises(ValueError):
            compute_metrics(f, a)


# ---------------------------------------------------------------------------
# compute_metrics_by_horizon
# ---------------------------------------------------------------------------

class TestComputeMetricsByHorizon:

    def test_groups_into_correct_buckets(self):
        """
        Rows at horizons 4h, 5h → bucket centre 3h (0-6h bucket centre = 3)
        Rows at horizons 7h, 8h → bucket centre 9h (6-12h bucket centre = 9)
        """
        df = pd.DataFrame({
            "forecast_mw": [110, 120, 210, 220],
            "actual_mw":   [100, 100, 200, 200],
            "horizon_hours": [4.0, 5.0, 7.0, 8.0],
        })
        buckets = compute_metrics_by_horizon(df, bucket_size_hours=6.0)
        assert len(buckets) == 2
        centres = [b.horizon_hours for b in buckets]
        assert 3.0 in centres
        assert 9.0 in centres

    def test_mae_per_bucket(self):
        """First bucket: errors [10, 20] → MAE 15."""
        df = pd.DataFrame({
            "forecast_mw": [110, 120],
            "actual_mw":   [100, 100],
            "horizon_hours": [4.0, 5.0],
        })
        buckets = compute_metrics_by_horizon(df, bucket_size_hours=6.0)
        assert len(buckets) == 1
        assert buckets[0].mae == pytest.approx(15.0)
        assert buckets[0].sample_count == 2

    def test_empty_input_returns_empty_list(self):
        df = pd.DataFrame(columns=["forecast_mw", "actual_mw", "horizon_hours"])
        assert compute_metrics_by_horizon(df) == []

    def test_sorted_ascending_by_horizon(self):
        df = pd.DataFrame({
            "forecast_mw": [100, 100, 100],
            "actual_mw":   [90, 90, 90],
            "horizon_hours": [25.0, 5.0, 13.0],
        })
        buckets = compute_metrics_by_horizon(df, bucket_size_hours=6.0)
        centres = [b.horizon_hours for b in buckets]
        assert centres == sorted(centres)


# ---------------------------------------------------------------------------
# compute_error_histogram
# ---------------------------------------------------------------------------

class TestComputeErrorHistogram:

    def test_bin_counts_sum_to_n(self):
        """All data points must fall into some bin."""
        f = _s(110, 90, 120, 80, 100)
        a = _s(100, 100, 100, 100, 100)
        bins = compute_error_histogram(f, a, n_bins=5)
        assert sum(b.count for b in bins) == 5

    def test_positive_errors_land_in_right_half(self):
        """Over-forecasts (positive errors) must be in bins with bin_left >= 0."""
        f = _s(200, 200, 200)
        a = _s(100, 100, 100)
        bins = compute_error_histogram(f, a, n_bins=4)
        for b in bins:
            if b.count > 0:
                assert b.bin_left >= 0

    def test_bin_edges_are_contiguous(self):
        """bin_right[i] == bin_left[i+1] for adjacent bins."""
        f = _s(100, 110, 90, 105, 95)
        a = _s(100, 100, 100, 100, 100)
        bins = compute_error_histogram(f, a, n_bins=5)
        for i in range(len(bins) - 1):
            assert abs(bins[i].bin_right - bins[i + 1].bin_left) < 1e-9

    def test_empty_input_returns_empty(self):
        f = pd.Series([], dtype=float)
        a = pd.Series([], dtype=float)
        assert compute_error_histogram(f, a) == []


# ---------------------------------------------------------------------------
# error_band_from_history
# ---------------------------------------------------------------------------

class TestErrorBandFromHistory:

    def test_p10_p90_hand_calculated(self):
        """
        errors (f - a) = [-200, -100, 0, 100, 200, 300, 400, 500, 600, 700]
        P10 = -110, P90 = 610  (well-separated, sign clearly different)
        """
        errors = [-200, -100, 0, 100, 200, 300, 400, 500, 600, 700]
        forecast = pd.Series([e + 1000 for e in errors], dtype=float)
        actual   = pd.Series([1000.0] * len(errors), dtype=float)
        df = pd.DataFrame({"forecast_mw": forecast, "actual_mw": actual})
        p10, p90 = error_band_from_history(df)
        assert p10 is not None and p90 is not None
        assert p10 < p90
        assert p10 < 0     # net under-forecast at P10
        assert p90 > 0     # net over-forecast at P90

    def test_returns_none_none_for_single_row(self):
        df = pd.DataFrame({"forecast_mw": [100.0], "actual_mw": [90.0]})
        assert error_band_from_history(df) == (None, None)

    def test_returns_none_none_for_empty(self):
        df = pd.DataFrame({"forecast_mw": pd.Series([], dtype=float),
                           "actual_mw":   pd.Series([], dtype=float)})
        assert error_band_from_history(df) == (None, None)

