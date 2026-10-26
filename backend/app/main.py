"""
app/main.py
============
FastAPI application.

Deployed as a Vercel serverless function via api/index.py.
Frontend (Vite/React) is served by Vercel from frontend/dist/.
Both live on the same domain so no CORS configuration is needed in production.

For local development, CORS is allowed from the Vite dev server (localhost:5173).
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


@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Allow local Vite dev server. Not needed in Vercel production (same domain).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000","https://energy-forecast-2z7m.onrender.com","https://energy-forecast-vpf8.vercel.app/"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(actuals.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")