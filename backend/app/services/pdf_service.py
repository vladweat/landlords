"""Сервис генерации PDF договоров."""

import os
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID, uuid4

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.core.exceptions import NotFoundError
from app.domain.entities import DocumentEntity
from app.domain.interfaces import IContractRepository, IDocumentRepository, IPropertyRepository, ITenantRepository

STORAGE_DIR = "/app/storage/documents"
FONT_PATH = "/app/fonts/DejaVuSans.ttf"
FONT_BOLD_PATH = "/app/fonts/DejaVuSans-Bold.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('DejaVu', FONT_PATH))
    FONT_NAME = 'DejaVu'
else:
    FONT_NAME = 'Helvetica'

if os.path.exists(FONT_BOLD_PATH):
    pdfmetrics.registerFont(TTFont('DejaVuBold', FONT_BOLD_PATH))
    FONT_BOLD = 'DejaVuBold'
else:
    FONT_BOLD = 'Helvetica-Bold'


class PdfService:
    """Сервис генерации PDF-документов."""

    def __init__(
        self,
        contract_repo: IContractRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
        document_repo: IDocumentRepository | None = None,
    ) -> None:
        self.contract_repo = contract_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo
        self.document_repo = document_repo

    def generate_contract_pdf(self, contract_id: UUID, account_id: UUID) -> bytes:
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract {contract_id} not found")

        prop = self.property_repo.get_by_id(contract.property_id, account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
        
        # Предполагаем, что у вас есть данные о владельце (арендодателе)
        # Если нет - нужно получить из репозитория
        # owner = self.owner_repo.get_by_property_id(prop.id, account_id)
        owner_name = "_____________________________"  # Заглушка, нужно заменить на реальные данные

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        left_margin = 22 * mm
        right_col = left_margin + 75 * mm
        y = height - 18 * mm

        def draw_line(text: str, y_pos: float, bold: bool = False, size: int = 9, x: float = None) -> float:
            c.setFont(FONT_BOLD if bold else FONT_NAME, size)
            c.drawString(x or left_margin, y_pos, text)
            return y_pos - 4.5 * mm

        def draw_centered(text: str, y_pos: float, bold: bool = False, size: int = 9) -> float:
            c.setFont(FONT_BOLD if bold else FONT_NAME, size)
            c.drawCentredString(width / 2, y_pos, text)
            return y_pos - 4.5 * mm

        def check_space(y_pos: float, needed: float = 25 * mm) -> float:
            if y_pos < needed:
                c.showPage()
                return height - 18 * mm
            return y_pos

        # Получаем данные из объектов
        tenant_name = tenant.full_name if tenant else "_____________________________"
        owner_name = owner_name  # Нужно получить из репозитория
        
        prop_address = prop.get_address() if prop else "_____________________________"
        city = prop.city if prop else "______________"
        street = prop.street if prop else "______________"
        house = prop.house if prop else "____"
        building = prop.building if prop else ""
        apartment = prop.apartment if prop else "____"

        address = f"г. {city}, ул. {street}, д. {house}"
        if building:
            address += f", корп. {building}"
        if apartment:
            address += f", кв. {apartment}"
        
        # Расчет количества месяцев
        if contract.end_date and contract.start_date:
            months = (contract.end_date.year - contract.start_date.year) * 12 + (contract.end_date.month - contract.start_date.month) + 1
        else:
            months = "____"
        
        # Форматирование дат
        start_date_str = contract.start_date.strftime('%d.%m.%Y') if contract.start_date else "___________"
        end_date_str = contract.end_date.strftime('%d.%m.%Y') if contract.end_date else "___________"
        
        # Данные для заполнения шаблона
        current_year = datetime.now().year
        current_city = "______________"
        current_day = "___"
        current_month = "__________"
        
        # Данные для п.4
        rent_amount = contract.rent_amount if contract.rent_amount else "___________"
        currency = contract.currency if hasattr(contract, 'currency') else "руб."
        deposit_amount = contract.deposit_amount if contract.deposit_amount else "___________"
        payment_day = contract.payment_day if hasattr(contract, 'payment_day') and contract.payment_day else "____"
        
        # Данные для п.3.2
        notice_period = "2"  # Можно сделать переменной

        # Заголовок
        y = draw_centered("ДОГОВОР АРЕНДЫ КВАРТИРЫ", y, bold=True, size=13)
        y -= 3 * mm
        
        # Город и дата
        y = draw_line(f"г. {current_city}                                {current_day} {current_month} 20__ г.", y)
        y -= 3 * mm

        # Стороны - ОБРАТИТЕ ВНИМАНИЕ: первым идет АРЕНДОДАТЕЛЬ (владелец), вторым - НАНИМАТЕЛЬ (tenant)
        y = draw_line(f"Мы, нижеподписавшиеся, гражданин {owner_name}, именуемый в", y)
        y = draw_line('дальнейшем "Арендодатель", с одной стороны, и гражданин', y)
        y = draw_line(f'{tenant_name}, именуемый в дальнейшем "Наниматель", с другой стороны, заключили настоящий', y)
        y = draw_line("Договор о нижеследующем:", y)
        y -= 2 * mm

        # 1. Предмет договора
        y = check_space(y)
        y = draw_line("1. Предмет договора", y, bold=True)
        
        # Разбиваем адрес на части для заполнения шаблона
        full_address = f"{city} {street} {house}"
        if building and building != "____":
            full_address += f" корп.{building}"
        if apartment and apartment != "____":
            full_address += f" кв.{apartment}"
        
        y = draw_line("1.1. Арендодатель предоставляет, а Наниматель получает во временное", y)
        y = draw_line(f"пользование (аренду) квартиру, расположенную по адресу: {full_address}", y)
        
        # Добавляем информацию о площади, если есть
        if hasattr(prop, 'size_m2') and prop.size_m2:
            y = draw_line(f"общей площадью {prop.size_m2} м².", y)
        
        y = draw_line("1.2. Арендодатель предоставляет, а Наниматель получает во временное", y)
        y = draw_line("пользование находящиеся в квартире предметы мебели и бытовую технику.", y)
        y = draw_line(f"1.3. Срок аренды составляет {months} месяцев и определяется", y)
        y = draw_line(f"с {start_date_str} по {end_date_str}.", y)
        y = draw_line("1.4. Передаваемая в аренду квартира используется Нанимателем только для", y)
        y = draw_line("проживания без права сдачи её в субаренду.", y)
        y -= 2 * mm

        # 2. Права и обязанности Арендодателя
        y = check_space(y)
        y = draw_line("2. Права и обязанности Арендодателя", y, bold=True)
        y = draw_line("2.1. Арендодатель подтверждает, что он получил согласие всех", y)
        y = draw_line("совершеннолетних лиц, зарегистрированных по данному адресу, или", y)
        y = draw_line("владеющих совместно с ним данной жилплощадью, на сдачу данной", y)
        y = draw_line("квартиры в аренду.", y)
        y = draw_line("2.2. Арендодатель подтверждает, что на момент подписания настоящего", y)
        y = draw_line("Договора аренды данная квартира не продана, не подарена, не является", y)
        y = draw_line("предметом судебного спора, не находится под залогом, арестом, не", y)
        y = draw_line("сдана внаем. Дом на период аренды квартиры не подлежит сносу или", y)
        y = draw_line("капитальному ремонту с отселением.", y)
        y = draw_line("2.3. Арендодатель имеет право посещать Нанимателя только с", y)
        y = draw_line("предварительным уведомлением.", y)
        y = draw_line("2.4. Арендодатель последствия аварий и повреждений, происшедших не по", y)
        y = draw_line("вине Нанимателя, устраняет своими силами.", y)
        y = draw_line("2.5. Арендодатель оплачивает: эксплуатационные расходы, центральное", y)
        y = draw_line("отопление, коммунальные услуги, телефон (абонентская ежемесячная", y)
        y = draw_line("плата).", y)
        y -= 2 * mm

        # 3. Права и обязанности Нанимателя
        y = check_space(y)
        y = draw_line("3. Права и обязанности Нанимателя", y, bold=True)
        y = draw_line("3.1. Содержать арендуемую квартиру в порядке, предусмотренном", y)
        y = draw_line("санитарными, противопожарными и иными нормами, установленными", y)
        y = draw_line("действующим законодательством РФ.", y)
        y = draw_line(f"3.2. О предстоящем освобождении снимаемой в аренду квартиры известить", y)
        y = draw_line(f"Арендодателя не менее чем за {notice_period} недели.", y)
        y = draw_line("3.3. В случае нанесения ущерба арендуемой квартире и имуществу,", y)
        y = draw_line("находящемуся в ней, Наниматель обязуется возместить Арендодателю", y)
        y = draw_line("причиненный ущерб.", y)
        y = draw_line("3.4. Наниматель оплачивает: расход электроэнергии, междугородние,", y)
        y = draw_line("международные телефонные переговоры, различные услуги телефонной", y)
        y = draw_line("связи.", y)
        y = draw_line("3.5. Нанимателю разрешено сдавать квартиру полностью или частично в", y)
        y = draw_line("субаренду физическим и юридическим лицам.", y)
        y -= 2 * mm

        # 4. Порядок расчетов
        y = check_space(y)
        y = draw_line("4. Порядок расчетов", y, bold=True)
        y = draw_line(f"4.1. За арендуемую квартиру Нанимателем уплачивается месячная плата", y)
        
        # Обработка валюты
        if currency.upper() in ['USD', '$']:
            y = draw_line(f"из расчета {rent_amount} рублей, что составляет эквивалентную сумму", y)
            y = draw_line(f"________ $ США по курсу ЦБ на день оплаты.", y)
        else:
            y = draw_line(f"из расчета {rent_amount} {currency}.", y)
        
        y = draw_line(f"4.2. Ежемесячная арендная плата вносится Нанимателем за месяц вперед", y)
        y = draw_line(f"не позднее {payment_day}-го числа.", y)
        y = draw_line("4.3. При подписании Договора Нанимателем вносится Арендодателю оплата", y)
        y = draw_line(f"за месяц вперёд в размере {rent_amount} {currency}, а также залоговая", y)
        y = draw_line(f"сумма {deposit_amount} {currency}, которая возвращается Нанимателю при", y)
        y = draw_line("выезде его из квартиры.", y)
        y = draw_line("4.4. Размер арендной платы остаётся неизменным в течение", y)
        y = draw_line("всего срока действия настоящего договора.", y)
        y -= 2 * mm

        # 5. Срок действия договора
        y = check_space(y)
        y = draw_line("5. Срок действия договора аренды квартиры, порядок изменения,", y, bold=True)
        y = draw_line("расторжение договора", y, bold=True)
        y = draw_line("5.1. Настоящий договор вступает в силу с момента его подписания и", y)
        y = draw_line("действует в течение всего срока аренды квартиры.", y)
        y = draw_line("5.2. Изменения и дополнения к настоящему договору могут вноситься", y)
        y = draw_line("только по соглашению сторон путем подписания дополнительного", y)
        y = draw_line("соглашения, являющегося неотъемлемой частью настоящего договора", y)
        y = draw_line("аренды квартиры.", y)
        y = draw_line("5.3. Досрочное расторжение договора аренды Арендодателем возможно в", y)
        y = draw_line("случаях, если Наниматель нарушил свои обязанности по настоящему", y)
        y = draw_line("договору аренды квартиры.", y)
        y -= 2 * mm

        # 6. Порядок рассмотрения споров
        y = check_space(y)
        y = draw_line("6. Порядок рассмотрения споров", y, bold=True)
        y = draw_line("6.1. Все споры между сторонами, связанные с настоящим договором", y)
        y = draw_line("аренды, решаются путем взаимных переговоров.", y)
        y = draw_line("6.2. В случае невозможности их разрешения переговорным путем они", y)
        y = draw_line("будут рассмотрены в соответствии с Законодательством РФ.", y)
        y -= 3 * mm

        # 7. Паспортные данные сторон
        y = check_space(y, 55 * mm)
        y = draw_line("7. Паспортные данные сторон", y, bold=True)
        y -= 2 * mm
        
        c.setFont(FONT_NAME, 9)
        
        # Левая колонка — Арендодатель (владелец)
        c.drawString(left_margin, y, "Арендодатель:")
        c.drawString(right_col, y, "Наниматель:")
        y -= 5 * mm
        
        # Имена
        c.drawString(left_margin, y, owner_name)
        c.drawString(right_col, y, tenant_name)
        y -= 5 * mm
        
        # Паспортные данные - оставляем пустые поля для заполнения
        c.drawString(left_margin, y, "Паспорт: серия _____ № _______________")
        c.drawString(right_col, y, "Паспорт: серия ______ № _______________")
        y -= 5 * mm
        
        c.drawString(left_margin, y, "выдан: _______________________________")
        c.drawString(right_col, y, "выдан: ________________________________")
        y -= 5 * mm
        
        c.drawString(left_margin, y, "Зарегистрирован по адресу: ___________")
        c.drawString(right_col, y, "Зарегистрирован по адресу: ____________")
        y -= 5 * mm
        
        c.drawString(left_margin, y, "______________________________________")
        c.drawString(right_col, y, "_______________________________________")
        y -= 8 * mm
        
        c.drawString(left_margin, y, "Подпись___________________")
        c.drawString(right_col, y, "Подпись___________________")

        c.showPage()
        c.save()
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

    def generate_and_save(self, contract_id: UUID, account_id: UUID) -> DocumentEntity:
        """Сгенерировать PDF договора и сохранить на диск."""
        pdf_bytes = self.generate_contract_pdf(contract_id, account_id)
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
