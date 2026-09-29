"""Маршруты экспорта финансовых отчётов."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_current_account_id, get_report_export_service
from app.services.report_export_service import ReportExportService

router = APIRouter(prefix="/v1/reports", tags=["Reports"])


@router.get("/export")
def export_report(
    start_date: date = Query(..., description="Начало периода"),
    end_date: date = Query(..., description="Конец периода"),
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    contract_ids: list[UUID] | None = Query(
        None, description="Ограничить отчёт выбранными договорами"
    ),
    account_id: UUID = Depends(get_current_account_id),
    service: ReportExportService = Depends(get_report_export_service),
) -> Response:
    """Скачать отчёт за период (XLSX или CSV) для налоговой/бухгалтерии."""
    content, media_type, filename = service.export(
        account_id,
        start_date,
        end_date,
        fmt=format,
        contract_ids=contract_ids,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
