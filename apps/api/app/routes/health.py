from fastapi import APIRouter
from seal_core.pipeline.trust import is_trust_explainability_enabled

from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Liveness check."""
    return HealthResponse(
        status="ok",
        trust_explainability_enabled=is_trust_explainability_enabled(),
    )
