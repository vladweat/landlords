"""Установка RLS-контекста аккаунта для текущей транзакции."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_tenant_context(session: Session, account_id: UUID) -> None:
    """Установить аккаунт транзакционно, без commit или изменения Session lifecycle."""
    session.execute(
        text("SELECT set_config('app.account_id', :account_id, true)"),
        {"account_id": str(account_id)},
    )
