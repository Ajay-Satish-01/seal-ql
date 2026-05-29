from fastapi import APIRouter

from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Liveness check."""
    return HealthResponse(status="ok")
