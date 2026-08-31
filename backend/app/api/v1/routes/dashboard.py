"""Маршруты для дашборда."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_dashboard_service
from app.api.v1.schemas.dashboard_schema import DashboardResponse, DashboardSummaryResponse
from app.services.dashboard_service import DashboardService
from app.api.responses import success_response, success_list_response
from app.api.deps import get_payment_repo, get_contract_repo, get_property_repo, get_tenant_repo
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.payment_repo import PaymentRepository

router = APIRouter(prefix="/v1/dashboard", tags=["Dashboard"])


from app.api.deps import get_roi_service
from app.services.roi_service import RoiService

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

from app.api.deps import get_forecast_service
from app.services.forecast_service import ForecastService


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
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    limit: int = 5,
) -> dict:
    """Последние платежи для дашборда с адресом и арендатором."""
    payments = payment_repo.list_by_account(account_id)[:limit]
    data = []
    for p in payments:
        contract = contract_repo.get_by_id(p.contract_id, account_id)
        address = ""
        tenant_name = ""
        if contract:
            prop = property_repo.get_by_id(contract.property_id, account_id)
            if prop:
                address = prop.get_address()
            tenant = tenant_repo.get_by_id(contract.tenant_id, account_id)
            if tenant:
                tenant_name = tenant.full_name
        data.append({
            "id": str(p.id),
            "contract_id": str(p.contract_id),
            "amount": float(p.amount),
            "date_paid": p.date_paid.isoformat(),
            "method": p.method,
            "property_address": address,
            "tenant_name": tenant_name,
        })
    return {"status": "success", "data": data}