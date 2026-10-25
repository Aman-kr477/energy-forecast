# Wind Forecast Dashboard

Decision-support web app for a UK energy utility day-ahead wind power buying team.
Built on Elexon BMRS open data (January 2026). No login required.

> **AI disclosure**: This project was built with significant AI tool assistance
> (code generation, debugging, and documentation).

---

## Live deployment

Add your Heroku app URL here once deployed.

---

## What it does

| Screen | Purpose |
|--------|--------|
| **Forecast for decision** | Shows the wind generation forecast available at the buyers decision cutoff. The error band shows historical accuracy. |
| **Forecast accuracy** | MAE, RMSE, bias, P90 across January 2026 at a selectable forecast horizon. |

---

## Definitions

| Term | Definition |
|------|----------|
| Delivery day | The day electricity is physically delivered (Jan 2 - Feb 1 2026). |
| Decision cutoff | Default 09:00 Europe/London on the day before delivery. User-configurable. |
| Latest forecast at cutoff | For each 30-min delivery slot, the forecast with the greatest publishTime that is <= cutoff. No look-ahead. |
| Horizon (hours) | startTime minus publishTime in hours. |
| Error | forecast_mw minus actual_mw. Positive = over-forecast. |
| MAE | Mean absolute error. |
| RMSE | Root mean squared error. |
| Bias | Mean signed error (+ = over-forecast tendency). |
| P90 abs error | 90th percentile of absolute errors. |
| Normalised MAE | MAE divided by mean actual. MAPE not used (actuals near zero). |
| Error band | P10/P90 of signed errors from prior delivery days only (no leakage). |

---

## Data sources

| Stream | Resolution | Notes |
|--------|-----------|-------|
| FUELHH (actuals) | 30 min | fuelType=WIND filter |
| WINDFOR (forecasts) | 60 min upsampled to 30 min | Wind-only stream |

Upsampling: each hourly WINDFOR value is repeated for both the :00 and :30 half-hour slots.
Data is fetched once and stored as Parquet. The app never calls Elexon at request time.

---

## Folder layout

`
.
|-- backend/
|   |-- app/
|   |   |-- api/routes/     # FastAPI route handlers
|   |   |-- clients/        # Elexon API client with retry
|   |   |-- schemas/        # Pydantic response models
|   |   |-- services/       # Pure logic: forecast_selector, metrics
|   |   |-- utils/          # Data loader, timezone helpers
|   |-- scripts/ingest.py   # One-shot data pull
|   |-- data/               # Parquet snapshots (git-ignored)
|   |-- tests/              # pytest tests
|   |-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- components/     # ui/, charts/, common/
|   |   |-- features/       # decision/, accuracy/
|   |   |-- hooks/          # useApi hook
|   |   |-- lib/            # API client, format utils
|   |   |-- store/          # Zustand filter state
|   |   |-- types/          # Shared TypeScript types
|-- Dockerfile              # Multi-stage build
|-- docker-compose.yml
|-- heroku.yml
|-- .env.example
|-- README.md
`

---

## Running locally

### With Docker

`ash
# 1. Generate data (one-time, ~2 min)
cd backend && pip install -r requirements.txt && python scripts/ingest.py

# 2. Build and run from repo root
cd .. && docker build -t wind-dashboard . && docker compose up
`

### Without Docker

Backend:
`ash
cd backend
pip install -r requirements.txt
python scripts/ingest.py
uvicorn app.main:app --reload
`

Frontend (separate terminal):
`ash
cd frontend && npm install && npm run dev
# Vite proxies /api calls to the backend
`

---

## Regenerating data

`ash
cd backend && python scripts/ingest.py
`

Re-fetches January 2026 from Elexon BMRS (~2 min, 63 chunked API calls).

---

## Deploying to Heroku

`ash
heroku create your-app-name
heroku stack:set container -a your-app-name
# Include data snapshots (remove from .gitignore first)
git add backend/data/ && git commit -m " add snapshots\n# energy-forecast
