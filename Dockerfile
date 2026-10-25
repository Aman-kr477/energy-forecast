# Backend API - deployed to Railway (or any Docker host).
# Frontend is deployed separately to Vercel.
#
# Data snapshots (actuals.parquet, forecasts.parquet) are committed to the repo
# and baked into this image at build time. Regenerate with: python scripts/ingest.py
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
RUN test -f data/actuals.parquet && test -f data/forecasts.parquet || (echo 'ERROR: missing data snapshots' && exit 1)
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

