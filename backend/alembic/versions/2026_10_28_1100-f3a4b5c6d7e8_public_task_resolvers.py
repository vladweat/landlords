"""Добавить резолверы публичных ссылок и пакетной обработки."""

from typing import Sequence, Union

from alembic import op

from app.core.config import settings

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Разрешить runtime только определить tenant scope по токену или ID."""
    op.execute(
        """
        CREATE FUNCTION public.app_account_id_for_invoice_token(p_token text)
        RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT invoice.account_id
            FROM public.invoices AS invoice
            WHERE invoice.public_token = p_token
              AND invoice.public_token_expires_at > CURRENT_TIMESTAMP
            LIMIT 1
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.app_account_id_for_portal_token(p_token text)
        RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT contract.account_id
            FROM public.contracts AS contract
            WHERE contract.portal_token = p_token
              AND contract.portal_token_expires_at > CURRENT_TIMESTAMP
            LIMIT 1
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.app_account_ids()
        RETURNS TABLE(account_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT account.id FROM public.accounts AS account
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.app_outbox_account_ids()
        RETURNS TABLE(account_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT DISTINCT message.account_id
            FROM public.task_outbox AS message
            WHERE message.status IN ('pending', 'published')
              AND message.available_at <= CURRENT_TIMESTAMP
              AND (message.lease_until IS NULL
                   OR message.lease_until <= CURRENT_TIMESTAMP)
            ORDER BY message.account_id
        $$
        """
    )
    bind = op.get_bind()
    runtime_role = bind.dialect.identifier_preparer.quote(settings.DB_USER)
    resolver_role = bind.dialect.identifier_preparer.quote("landlords_rls_resolver")
    resolver_grants = (
        "GRANT SELECT (public_token, public_token_expires_at, account_id) "
        "ON TABLE public.invoices TO "
        f"{resolver_role}",
        "GRANT SELECT (portal_token, portal_token_expires_at, account_id) "
        "ON TABLE public.contracts TO "
        f"{resolver_role}",
        f"GRANT SELECT (id) ON TABLE public.accounts TO {resolver_role}",
        "GRANT SELECT (account_id, status, available_at, lease_until) "
        "ON TABLE public.task_outbox TO "
        f"{resolver_role}",
    )
    for statement in resolver_grants:
        op.execute(statement)
    signatures = (
        "public.app_account_id_for_invoice_token(text)",
        "public.app_account_id_for_portal_token(text)",
        "public.app_account_ids()",
        "public.app_outbox_account_ids()",
    )
    for signature in signatures:
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"ALTER FUNCTION {signature} OWNER TO {resolver_role}")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {runtime_role}")


def downgrade() -> None:
    """Удалить resolver-функции."""
    signatures = (
        "public.app_account_ids()",
        "public.app_outbox_account_ids()",
        "public.app_account_id_for_portal_token(text)",
        "public.app_account_id_for_invoice_token(text)",
    )
    for signature in signatures:
        op.execute(f"DROP FUNCTION {signature}")
    op.execute(
        "REVOKE SELECT (public_token, public_token_expires_at, account_id) "
        "ON TABLE public.invoices FROM landlords_rls_resolver"
    )
    op.execute(
        "REVOKE SELECT (portal_token, portal_token_expires_at, account_id) "
        "ON TABLE public.contracts FROM landlords_rls_resolver"
    )
    op.execute(
        "REVOKE SELECT (id) ON TABLE public.accounts FROM landlords_rls_resolver"
    )
    op.execute(
        "REVOKE SELECT (account_id, status, available_at, lease_until) "
        "ON TABLE public.task_outbox FROM landlords_rls_resolver"
    )
