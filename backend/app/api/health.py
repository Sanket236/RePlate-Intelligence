"""Health check endpoint."""
from fastapi import APIRouter

from app.core.config import APP_VERSION, LLM_ENABLED
from app.services.ml_service import ml_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", summary="Backend health and model readiness")
def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "model_ready": ml_service.is_ready,
        "llm_enabled": LLM_ENABLED,
    }
