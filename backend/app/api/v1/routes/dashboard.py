"""Маршруты для дашборда."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_dashboard_service, get_forecast_service, get_roi_service
from app.api.v1.schemas.dashboard_schema import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService
from app.services.forecast_service import ForecastService
from app.services.roi_service import RoiService

router = APIRouter(prefix="/v1/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_summary(
    account_id: UUID = Depends(get_current_account_id),
    service: DashboardService = Depends(get_dashboard_service),
    roi_service: RoiService = Depends(get_roi_service),
) -> dict:
    summary = service.get_summary(account_id)
    portfolio = roi_service.calculate_portfolio_roi(account_id)
    result = DashboardSummaryResponse.model_validate(summary.model_dump()).model_dump()
    result["portfolio_roi"] = portfolio
    result["properties_overview"] = summary.properties_overview
    return {"status": "success", "data": result}


@router.get("/forecast")
def get_forecast(
    account_id: UUID = Depends(get_current_account_id),
    service: ForecastService = Depends(get_forecast_service),
) -> dict:
    """Прогноз дохода до конца года."""
    result = service.get_forecast(account_id)
    return {"status": "success", "data": result}


@router.get("/last-payments")
def get_last_payments(
    account_id: UUID = Depends(get_current_account_id),
    service: DashboardService = Depends(get_dashboard_service),
    limit: int = 5,
) -> dict:
    """Последние платежи для дашборда с адресом и арендатором."""
    data = service.get_last_payments(account_id, limit=limit)
    return {"status": "success", "data": data}
