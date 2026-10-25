"""
app/api/routes/meta.py
=======================
GET /api/meta  – available dates, horizons, default cutoff.
"""
from __future__ import annotations

import math
from fastapi import APIRouter
from app.schemas.responses import MetaResponse
from app.utils import data_loader
from app.utils.time_utils import DEFAULT_CUTOFF_LOCAL

router = APIRouter()


@router.get("/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    """Return available delivery dates, horizon list, and default cutoff."""
    act = data_loader.actuals
    fct = data_loader.forecasts

    # Delivery dates = unique dates present in actuals
    if act.empty:
        dates: list[str] = []
    else:
        dates = sorted(
            act["start_time"].dt.normalize().dt.date.astype(str).unique().tolist()
        )

    # Distinct horizons (rounded to 1 dp to avoid float noise)
    if fct.empty:
        horizons: list[float] = []
    else:
        raw = (
            (fct["start_time"] - fct["publish_time"])
            .dt.total_seconds()
            .div(3600)
        )
        horizons = sorted({round(h, 1) for h in raw if not math.isnan(h) and h > 0})

    return MetaResponse(
        delivery_dates=dates,
        available_horizons=horizons,
        default_cutoff=DEFAULT_CUTOFF_LOCAL.strftime("%H:%M"),
        timezone="Europe/London",
    )

