"""
app/main.py
============
FastAPI application entry point.

Loads data into memory on startup, mounts all routers under /api.

Deployment split:
  - Backend  → Heroku (this file)
  - Frontend → Vercel

CORS is configured to allow the Vercel production domain and the local
Vite dev server. Set the ALLOWED_ORIGINS env var (comma-separated) to
add your Vercel URL before deploying.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import actuals, forecast, health, metrics, meta
from app.utils import data_loader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS: allow Vercel frontend + local dev
# Add your Vercel URL via  ALLOWED_ORIGINS=https://your-app.vercel.app
# ---------------------------------------------------------------------------
_default_origins = "http://localhost:5173,http://localhost:3000"
_raw = os.environ.get("ALLOWED_ORIGINS", _default_origins)
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data snapshots before serving any requests."""
    log.info("Loading data snapshots ...")
    data_loader.load()
    log.info("Startup complete.")
    yield
    log.info("Shutting down.")


app = FastAPI(
    title="Wind Forecast Dashboard API",
    description="Day-ahead wind generation forecast and accuracy for GB energy buyers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(actuals.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")