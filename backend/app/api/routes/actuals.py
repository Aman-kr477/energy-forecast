"""
app/api/routes/actuals.py
==========================
GET /api/actuals?start=YYYY-MM-DD&end=YYYY-MM-DD
"""
from __future__ import annotations

from datetime import date, timezone
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.schemas.responses import ActualPoint, ActualsResponse
from app.utils import data_loader

router = APIRouter()


@router.get("/actuals", response_model=ActualsResponse)
def get_actuals(
    start: date = Query(..., description="Start date inclusive (YYYY-MM-DD)"),
    end: date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
) -> ActualsResponse:
    """Return 30-min wind actuals for the requested date range."""
    if end < start:
        raise HTTPException(status_code=422, detail="end must be >= start")

    start_dt = pd.Timestamp(start, tz="UTC")
    end_dt = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)  # inclusive end

    df = data_loader.actuals
    mask = (df["start_time"] >= start_dt) & (df["start_time"] < end_dt)
    subset = df[mask].sort_values("start_time")

    if subset.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No actuals data for range {start} – {end}",
        )

    return ActualsResponse(
        data=[
            ActualPoint(
                start_time=row.start_time.isoformat(),
                generation_mw=row.generation,
            )
            for row in subset.itertuples()
        ]
    )
