"""
tests/test_forecast_selector.py
================================
Unit tests for app/services/forecast_selector.py

Tests cover:
- Selector never uses a forecast published after the cutoff
- Selector picks the latest eligible forecast (not an earlier one)
- Slots with no eligible forecast return NaN/NaT
- horizon_hours is correctly calculated
- Full-day result always has exactly 48 rows
- Horizon-based selector respects the minimum lead-time rule
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from app.services.forecast_selector import (
    select_forecast_at_cutoff,
    select_forecast_at_horizon,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def _make_forecasts(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal forecasts DataFrame from a list of dicts."""
    if not rows:
        return pd.DataFrame(columns=["start_time", "publish_time", "generation"]).astype(
            {"start_time": "datetime64[ns, UTC]", "publish_time": "datetime64[ns, UTC]", "generation": "float64"}
        )
    df = pd.DataFrame(rows)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["generation"] = df["generation"].astype(float)
    return df


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DELIVERY_DATE = "2026-01-02"

# A realistic mini-dataset: one slot (00:00) with three forecast versions
@pytest.fixture()
def simple_forecasts() -> pd.DataFrame:
    return _make_forecasts([
        # Very early forecast (published 36 h before slot)
        {"start_time": "2026-01-02T00:00:00Z", "publish_time": "2025-12-31T12:00:00Z", "generation": 1000},
        # Mid forecast (published 18 h before slot)
        {"start_time": "2026-01-02T00:00:00Z", "publish_time": "2026-01-01T06:00:00Z", "generation": 1500},
        # Latest forecast BEFORE cutoff (published at 07:30, cutoff 09:00)
        {"start_time": "2026-01-02T00:00:00Z", "publish_time": "2026-01-01T07:30:00Z", "generation": 1800},
        # Post-cutoff forecast — must NEVER be selected
        {"start_time": "2026-01-02T00:00:00Z", "publish_time": "2026-01-01T11:30:00Z", "generation": 9999},
    ])


@pytest.fixture()
def multi_slot_forecasts() -> pd.DataFrame:
    """48-slot dataset: slot 00:00 has a pre-cutoff forecast; 23:30 does not."""
    rows = []
    day = pd.Timestamp("2026-01-02T00:00:00Z")
    cutoff_pub = pd.Timestamp("2026-01-01T07:30:00Z")
    for i in range(48):
        slot = day + pd.Timedelta(minutes=30 * i)
        if slot != pd.Timestamp("2026-01-02T23:30:00Z"):
            rows.append({
                "start_time": slot,
                "publish_time": cutoff_pub,
                "generation": 1000 + i,
            })
    return _make_forecasts(rows)


# ---------------------------------------------------------------------------
# select_forecast_at_cutoff tests
# ---------------------------------------------------------------------------

class TestSelectForecastAtCutoff:

    def test_always_returns_48_rows(self, simple_forecasts):
        """Result spine must have exactly one row per 30-min slot."""
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        assert len(result) == 48

    def test_picks_latest_eligible_forecast(self, simple_forecasts):
        """Must select the 07:30 publish, not the 06:00 one."""
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        row = result[result["start_time"] == _ts("2026-01-02T00:00:00Z")].iloc[0]
        assert row["forecast_mw"] == 1800.0
        assert row["publish_time"] == _ts("2026-01-01T07:30:00Z")

    def test_never_uses_post_cutoff_forecast(self, simple_forecasts):
        """The 9999 MW post-cutoff forecast must never appear."""
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        assert 9999.0 not in result["forecast_mw"].values

    def test_forecast_exactly_at_cutoff_is_eligible(self, simple_forecasts):
        """publish_time == cutoff is eligible (<=, not <)."""
        cutoff = _utc(2026, 1, 1, 7, 30)   # exactly matches the 07:30 row
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        row = result[result["start_time"] == _ts("2026-01-02T00:00:00Z")].iloc[0]
        assert row["forecast_mw"] == 1800.0

    def test_slot_with_no_eligible_forecast_is_null(self, multi_slot_forecasts):
        """Slot 23:30 has no forecast → NaN forecast_mw and NaT publish_time."""
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(multi_slot_forecasts, DELIVERY_DATE, cutoff)
        missing = result[result["start_time"] == _ts("2026-01-02T23:30:00Z")].iloc[0]
        assert pd.isna(missing["forecast_mw"])
        assert pd.isna(missing["publish_time"])
        assert pd.isna(missing["horizon_hours"])

    def test_all_slots_null_when_cutoff_before_all_publishes(self, simple_forecasts):
        """Cutoff before any publish → every slot is null."""
        cutoff = _utc(2025, 12, 1, 0, 0)   # way before any data
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        assert result["forecast_mw"].isna().all()

    def test_horizon_hours_calculated_correctly(self, simple_forecasts):
        """horizon = (start_time - publish_time) in hours."""
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        row = result[result["start_time"] == _ts("2026-01-02T00:00:00Z")].iloc[0]
        # 2026-01-02 00:00 minus 2026-01-01 07:30 = 16.5 h
        assert abs(row["horizon_hours"] - 16.5) < 1e-9

    def test_result_sorted_by_start_time(self, simple_forecasts):
        """Result must be in chronological order."""
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(simple_forecasts, DELIVERY_DATE, cutoff)
        times = result["start_time"].tolist()
        assert times == sorted(times)

    def test_empty_forecasts_dataframe(self):
        """Empty input → 48 rows of NaN."""
        empty = _make_forecasts([])
        cutoff = _utc(2026, 1, 1, 9, 0)
        result = select_forecast_at_cutoff(empty, DELIVERY_DATE, cutoff)
        assert len(result) == 48
        assert result["forecast_mw"].isna().all()


# ---------------------------------------------------------------------------
# select_forecast_at_horizon tests
# ---------------------------------------------------------------------------

class TestSelectForecastAtHorizon:

    @pytest.fixture()
    def horizon_forecasts(self) -> pd.DataFrame:
        """Single slot with forecasts at multiple lead times."""
        return _make_forecasts([
            # 30h before slot
            {"start_time": "2026-01-02T12:00:00Z", "publish_time": "2026-01-01T06:00:00Z", "generation": 500},
            # 20h before slot
            {"start_time": "2026-01-02T12:00:00Z", "publish_time": "2026-01-01T16:00:00Z", "generation": 600},
            # 10h before slot (too fresh for H=12 test)
            {"start_time": "2026-01-02T12:00:00Z", "publish_time": "2026-01-02T02:00:00Z", "generation": 700},
        ])

    def test_respects_minimum_horizon(self, horizon_forecasts):
        """At H=12, only rows published >= 12 h before slot are eligible."""
        start = _utc(2026, 1, 2, 0, 0)
        end = _utc(2026, 1, 3, 0, 0)
        result = select_forecast_at_horizon(horizon_forecasts, start, end, horizon_hours=12.0)
        slot = result[result["start_time"] == _ts("2026-01-02T12:00:00Z")].iloc[0]
        # 10h row is ineligible; latest eligible is the 20h row → generation 600
        assert slot["forecast_mw"] == 600.0

    def test_picks_latest_within_horizon_constraint(self, horizon_forecasts):
        """Latest eligible publish, not the earliest."""
        start = _utc(2026, 1, 2, 0, 0)
        end = _utc(2026, 1, 3, 0, 0)
        result = select_forecast_at_horizon(horizon_forecasts, start, end, horizon_hours=25.0)
        slot = result[result["start_time"] == _ts("2026-01-02T12:00:00Z")].iloc[0]
        # Only the 30h row qualifies
        assert slot["forecast_mw"] == 500.0

    def test_slot_null_when_no_row_meets_horizon(self, horizon_forecasts):
        """No forecast published early enough → NaN."""
        start = _utc(2026, 1, 2, 0, 0)
        end = _utc(2026, 1, 3, 0, 0)
        result = select_forecast_at_horizon(horizon_forecasts, start, end, horizon_hours=35.0)
        slot = result[result["start_time"] == _ts("2026-01-02T12:00:00Z")].iloc[0]
        assert pd.isna(slot["forecast_mw"])

    def test_empty_range_returns_empty(self, horizon_forecasts):
        """start == end → empty DataFrame."""
        t = _utc(2026, 1, 2, 0, 0)
        result = select_forecast_at_horizon(horizon_forecasts, t, t, horizon_hours=12.0)
        assert result.empty

