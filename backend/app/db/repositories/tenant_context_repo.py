"""Узкие resolver-запросы для токенов и системной обработки аккаунтов."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class TenantContextRepository:
    """Возвращает только account ID через ограниченные DB-функции."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def account_id_for_invoice_token(self, token: str) -> UUID | None:
        return self._account_id("app_account_id_for_invoice_token", token)

    def account_id_for_portal_token(self, token: str) -> UUID | None:
        return self._account_id("app_account_id_for_portal_token", token)

    def account_ids(self) -> list[UUID]:
        rows = self.session.execute(text("SELECT account_id FROM app_account_ids()"))
        return [UUID(str(row.account_id)) for row in rows]

    def outbox_account_ids(self) -> list[UUID]:
        rows = self.session.execute(
            text("SELECT account_id FROM app_outbox_account_ids()")
        )
        return [UUID(str(row.account_id)) for row in rows]

    def _account_id(self, function_name: str, token: str) -> UUID | None:
        value = self.session.execute(
            text(f"SELECT {function_name}(:token)"), {"token": token}
        ).scalar_one_or_none()
        return UUID(str(value)) if value is not None else None
