from fastapi import APIRouter
from app.config import settings
from app.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=settings.app_env,
    )
