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

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://energy-forecast-vpf8.vercel.app",   # no trailing slash
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(actuals.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")