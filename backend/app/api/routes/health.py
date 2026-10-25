"""app/api/routes/health.py"""
from fastapi import APIRouter
from app.schemas.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Simple liveness check."""
    return HealthResponse(status="ok")
