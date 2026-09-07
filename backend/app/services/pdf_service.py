"""Сервис генерации PDF договоров."""

import os
import re
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID, uuid4
from xml.sax.saxutils import escape

from jinja2 import BaseLoader, Environment, StrictUndefined, select_autoescape
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import DocumentEntity
from app.domain.interfaces import (
    IAccountRepository,
    IContractRepository,
    IDocumentRepository,
    IPropertyRepository,
    ITenantRepository,
    IUserRepository,
)
from app.services.contract_template_service import ContractTemplateService

STORAGE_DIR = "/app/storage/documents"
FONT_PATH = "/app/fonts/DejaVuSans.ttf"
FONT_BOLD_PATH = "/app/fonts/DejaVuSans-Bold.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))
    FONT_NAME = "DejaVu"
else:
    FONT_NAME = "Helvetica"

if os.path.exists(FONT_BOLD_PATH):
    pdfmetrics.registerFont(TTFont("DejaVuBold", FONT_BOLD_PATH))
    FONT_BOLD = "DejaVuBold"
else:
    FONT_BOLD = "Helvetica-Bold"

_MONTHS_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


class PdfService:
    """Сервис генерации PDF-документов."""

    def __init__(
        self,
        contract_repo: IContractRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
        document_repo: IDocumentRepository | None = None,
        template_service: ContractTemplateService | None = None,
        account_repo: IAccountRepository | None = None,
        user_repo: IUserRepository | None = None,
    ) -> None:
        self.contract_repo = contract_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo
        self.document_repo = document_repo
        self.template_service = template_service
        self.account_repo = account_repo
        self.user_repo = user_repo

    def generate_contract_pdf(
        self,
        contract_id: UUID,
        account_id: UUID,
        template_id: UUID | None = None,
    ) -> bytes:
        """Сгенерировать PDF договора по шаблону с плейсхолдерами."""
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract {contract_id} not found")

        prop = self.property_repo.get_by_id(contract.property_id, account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
        property_type = prop.type if prop else None

        if self.template_service is None:
            raise ValidationError("Сервис шаблонов не настроен")

        template = self.template_service.resolve_template(
            account_id, property_type, template_id=template_id
        )
        context = self._build_contract_context(contract, prop, tenant, account_id)
        title = self._render_jinja(template.title, context)
        body = self._render_jinja(template.body, context)
        return self._render_template_pdf(title, body)

    def _build_contract_context(self, contract, prop, tenant, account_id: UUID) -> dict:
        now = datetime.now(timezone.utc)
        owner_name = "_____________________________"
        if self.account_repo:
            account = self.account_repo.get_by_id(account_id)
            if account:
                if self.user_repo:
                    owner = self.user_repo.get_by_id(account.owner_id)
                    if owner and owner.full_name:
                        owner_name = owner.full_name
                    else:
                        owner_name = account.name
                else:
                    owner_name = account.name

        tenant_name = tenant.full_name if tenant else "_____________________________"
        prop_address = prop.get_address() if prop else "_____________________________"
        city = prop.city if prop else "______________"
        size_m2 = prop.size_m2 if prop and prop.size_m2 else ""
        property_type = prop.type if prop else ""

        start_date_str = (
            contract.start_date.strftime("%d.%m.%Y") if contract.start_date else "___________"
        )
        end_date_str = (
            contract.end_date.strftime("%d.%m.%Y") if contract.end_date else "___________"
        )
        rent_amount = contract.rent_amount if contract.rent_amount is not None else "___________"
        deposit_amount = (
            contract.deposit_amount if contract.deposit_amount is not None else "___________"
        )
        return {
            "owner_name": owner_name,
            "tenant_name": tenant_name,
            "property_address": prop_address,
            "property_type": property_type,
            "size_m2": size_m2,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "rent_amount": str(rent_amount),
            "currency": contract.currency or "RUB",
            "deposit_amount": str(deposit_amount),
            "payment_day": contract.payment_day or "____",
            "notice_period": "2",
            "city": city,
            "signing_day": str(now.day),
            "signing_month": _MONTHS_RU[now.month],
            "signing_year": str(now.year),
        }

    def _render_jinja(self, template_text: str, context: dict) -> str:
        env = Environment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            autoescape=select_autoescape(enabled_extensions=()),
        )
        try:
            return env.from_string(template_text).render(**context)
        except Exception as exc:
            raise ValidationError(f"Ошибка шаблона: {exc}") from exc

    def _render_template_pdf(self, title: str, body: str) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=22 * mm,
            rightMargin=22 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ContractTitle",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=13,
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=16,
        )
        body_style = ParagraphStyle(
            "ContractBody",
            parent=styles["Normal"],
            fontName=FONT_NAME,
            fontSize=10,
            alignment=TA_JUSTIFY,
            leading=14,
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "ContractHeading",
            parent=body_style,
            fontName=FONT_BOLD,
            spaceBefore=8,
            spaceAfter=4,
        )

        story = [Paragraph(escape(title), title_style), Spacer(1, 4 * mm)]
        for raw in re.split(r"\n\s*\n", body.strip()):
            chunk = raw.strip()
            if not chunk:
                continue
            html = escape(chunk).replace("\n", "<br/>")
            first_line = chunk.split("\n", 1)[0]
            is_heading = bool(re.match(r"^\d+\.\s+\S", first_line)) and "\n" not in chunk
            story.append(Paragraph(html, heading_style if is_heading else body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    def _save_pdf(
        self,
        contract_id: UUID,
        account_id: UUID,
        pdf_bytes: bytes,
        prefix: str,
        category: str | None = None,
    ) -> DocumentEntity:
        """Сохранить PDF на диск и создать запись документа."""
        dir_path = os.path.join(STORAGE_DIR, str(account_id), str(contract_id))
        os.makedirs(dir_path, exist_ok=True)

        filename = (
            f"{prefix}_{str(contract_id)[:8]}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        file_path = os.path.join(dir_path, filename)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        if category is None:
            if "invoice" in prefix:
                category = "invoice"
            elif "act" in prefix:
                category = "act"
            else:
                category = "contract_pdf"

        doc = DocumentEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract_id,
            filename=filename,
            file_path=file_path,
            category=category,
            mime_type="application/pdf",
            size_bytes=len(pdf_bytes),
            source="generated",
            title=filename,
        )
        if self.document_repo:
            return self.document_repo.create(doc)
        return doc

    def generate_and_save(
        self,
        contract_id: UUID,
        account_id: UUID,
        template_id: UUID | None = None,
    ) -> DocumentEntity:
        """Сгенерировать PDF договора и сохранить на диск."""
        pdf_bytes = self.generate_contract_pdf(
            contract_id, account_id, template_id=template_id
        )
        return self._save_pdf(contract_id, account_id, pdf_bytes, "contract")

    def generate_termination_act(
        self,
        contract_id: UUID,
        account_id: UUID,
        effective_date,
        reason: str,
    ) -> DocumentEntity:
        """Сгенерировать акт расторжения договора."""
        from datetime import date as date_cls

        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract {contract_id} not found")

        prop = self.property_repo.get_by_id(contract.property_id, account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)

        tenant_name = tenant.full_name if tenant else "_____________________________"
        prop_address = prop.get_address() if prop else "_____________________________"
        eff = effective_date if isinstance(effective_date, date_cls) else effective_date

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        left = 22 * mm
        y = height - 20 * mm

        def line(text: str, y_pos: float, bold: bool = False, size: int = 10) -> float:
            c.setFont(FONT_BOLD if bold else FONT_NAME, size)
            c.drawString(left, y_pos, text)
            return y_pos - 6 * mm

        c.setFont(FONT_BOLD, 14)
        c.drawCentredString(width / 2, y, "АКТ РАСТОРЖЕНИЯ ДОГОВОРА АРЕНДЫ")
        y -= 12 * mm

        y = line(f"Договор № {str(contract.id)[:8]}", y, bold=True)
        y = line(f"Объект: {prop_address}", y)
        y = line(f"Арендатор: {tenant_name}", y)
        y = line(
            f"Период договора: {contract.start_date.isoformat()} — "
            f"{contract.end_date.isoformat()}",
            y,
        )
        y = line(f"Дата расторжения: {eff.isoformat()}", y, bold=True)
        y -= 4 * mm
        y = line("Основание расторжения:", y, bold=True)
        words = reason.split()
        chunk = ""
        for word in words:
            trial = f"{chunk} {word}".strip()
            if len(trial) > 80:
                y = line(chunk, y)
                chunk = word
            else:
                chunk = trial
        if chunk:
            y = line(chunk, y)
        y -= 8 * mm
        y = line("Стороны подтверждают расторжение договора с указанной даты.", y)
        y = line("Взаимные расчёты производятся согласно условиям договора.", y)
        y -= 16 * mm
        y = line("Арендодатель: _________________ / _______________", y)
        y -= 8 * mm
        y = line("Арендатор:   _________________ / _______________", y)

        c.showPage()
        c.save()
        buffer.seek(0)
        return self._save_pdf(contract_id, account_id, buffer.read(), "termination_act")

    def generate_renewal_act(
        self,
        contract_id: UUID,
        account_id: UUID,
        old_end_date,
        new_end_date,
        new_rent_amount,
    ) -> DocumentEntity:
        """Сгенерировать дополнительное соглашение о продлении."""
        from decimal import Decimal

        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract {contract_id} not found")

        prop = self.property_repo.get_by_id(contract.property_id, account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)

        tenant_name = tenant.full_name if tenant else "_____________________________"
        prop_address = prop.get_address() if prop else "_____________________________"
        rent = Decimal(str(new_rent_amount))

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        left = 22 * mm
        y = height - 20 * mm

        def line(text: str, y_pos: float, bold: bool = False, size: int = 10) -> float:
            c.setFont(FONT_BOLD if bold else FONT_NAME, size)
            c.drawString(left, y_pos, text)
            return y_pos - 6 * mm

        c.setFont(FONT_BOLD, 13)
        c.drawCentredString(width / 2, y, "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ")
        y -= 7 * mm
        c.setFont(FONT_BOLD, 12)
        c.drawCentredString(width / 2, y, "о продлении договора аренды")
        y -= 12 * mm

        y = line(f"Договор № {str(contract.id)[:8]}", y, bold=True)
        y = line(f"Объект: {prop_address}", y)
        y = line(f"Арендатор: {tenant_name}", y)
        y = line(f"Дата начала договора: {contract.start_date.isoformat()}", y)
        y -= 4 * mm
        y = line("Стороны договорились о продлении договора на следующих условиях:", y)
        y = line(f"Прежняя дата окончания: {old_end_date.isoformat()}", y)
        y = line(f"Новая дата окончания: {new_end_date.isoformat()}", y, bold=True)
        y = line(f"Арендная плата: {rent} {contract.currency}", y, bold=True)
        y -= 8 * mm
        y = line("Остальные условия договора остаются без изменений.", y)
        y -= 16 * mm
        y = line("Арендодатель: _________________ / _______________", y)
        y -= 8 * mm
        y = line("Арендатор:   _________________ / _______________", y)

        c.showPage()
        c.save()
        buffer.seek(0)
        return self._save_pdf(contract_id, account_id, buffer.read(), "renewal_act")

    def generate_and_save_invoice(
        self,
        *,
        contract_id: UUID,
        account_id: UUID,
        landlord_name: str,
        tenant_name: str,
        property_address: str,
        period_start,
        period_end,
        due_date,
        amount,
        amount_paid,
        amount_remaining,
        currency: str,
        status: str,
        payment_details: str | None,
    ) -> DocumentEntity:
        """Сгенерировать PDF квитанции и сохранить на диск."""
        from decimal import Decimal

        status_labels = {
            "pending": "Ожидает оплаты",
            "partially_paid": "Частично оплачено",
            "paid": "Оплачено",
            "overdue": "Просрочено",
        }
        cur = "₽" if currency == "RUB" else currency
        amount_s = f"{Decimal(str(amount))} {cur}"
        paid_s = f"{Decimal(str(amount_paid))} {cur}"
        remaining_s = f"{Decimal(str(amount_remaining))} {cur}"

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        left = 22 * mm
        y = height - 20 * mm

        def line(text: str, y_pos: float, bold: bool = False, size: int = 10) -> float:
            c.setFont(FONT_BOLD if bold else FONT_NAME, size)
            c.drawString(left, y_pos, text)
            return y_pos - 6 * mm

        c.setFont(FONT_BOLD, 14)
        c.drawCentredString(width / 2, y, "КВИТАНЦИЯ НА ОПЛАТУ АРЕНДЫ")
        y -= 14 * mm

        y = line(f"Арендодатель: {landlord_name}", y, bold=True)
        y = line(f"Арендатор: {tenant_name}", y)
        y = line(f"Объект: {property_address}", y)
        y -= 2 * mm
        y = line(
            f"Период: {period_start.strftime('%d.%m.%Y')} — {period_end.strftime('%d.%m.%Y')}",
            y,
        )
        y = line(f"Срок оплаты: {due_date.strftime('%d.%m.%Y')}", y, bold=True)
        y = line(f"Статус: {status_labels.get(status, status)}", y)
        y -= 4 * mm
        y = line(f"Сумма начисления: {amount_s}", y)
        y = line(f"Уже оплачено: {paid_s}", y)
        y = line(f"К оплате: {remaining_s}", y, bold=True, size=12)
        y -= 6 * mm

        y = line("Реквизиты для оплаты:", y, bold=True)
        details = (payment_details or "").strip() or "Реквизиты не указаны арендодателем."
        words = details.replace("\n", " \n ").split()
        chunk = ""
        for word in words:
            if word == "\n":
                if chunk:
                    y = line(chunk, y)
                    chunk = ""
                y -= 2 * mm
                continue
            trial = f"{chunk} {word}".strip()
            if len(trial) > 85:
                y = line(chunk, y)
                chunk = word
            else:
                chunk = trial
        if chunk:
            y = line(chunk, y)

        c.showPage()
        c.save()
        buffer.seek(0)
        return self._save_pdf(
            contract_id, account_id, buffer.read(), "invoice", category="invoice"
        )

    def get_documents(self, contract_id: UUID, account_id: UUID) -> list[DocumentEntity]:
        if not self.document_repo:
            return []
        return self.document_repo.get_by_contract(contract_id, account_id)

    def get_document(self, doc_id: UUID, account_id: UUID) -> DocumentEntity:
        if not self.document_repo:
            raise NotFoundError("Document repository not available")
        doc = self.document_repo.get_by_id(doc_id, account_id)
        if not doc:
            raise NotFoundError(f"Document {doc_id} not found")
        return doc
