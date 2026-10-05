"""Публичный статус сервиса и контакты поддержки."""

from app.api.deps import get_status_service
from app.services.status_service import StatusService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/v1/public", tags=["Public Status"])


@router.get("/status")
def get_status(service: StatusService = Depends(get_status_service)) -> dict:
    """Текущий overall-статус и список инцидентов (без auth)."""
    return {"status": "success", "data": service.get_public_status()}
