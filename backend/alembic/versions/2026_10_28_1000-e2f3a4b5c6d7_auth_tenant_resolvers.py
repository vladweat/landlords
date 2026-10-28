"""Добавить узкие resolver-функции для публичной аутентификации."""

from typing import Sequence, Union

from alembic import op

from app.core.config import settings

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Возвращать только account ID для действующей identity/capability."""
    op.execute(
        """
        CREATE FUNCTION public.app_account_id_for_user(p_user_id uuid)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT membership.account_id
            FROM public.account_memberships AS membership
            WHERE membership.user_id = p_user_id
            LIMIT 1
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.app_account_id_for_invite_token(p_token text)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT invite.account_id
            FROM public.account_invites AS invite
            WHERE invite.token = p_token
            LIMIT 1
        $$
        """
    )

    bind = op.get_bind()
    runtime_role = bind.dialect.identifier_preparer.quote(settings.DB_USER)
    resolver_role = bind.dialect.identifier_preparer.quote("landlords_rls_resolver")
    op.execute(
        "GRANT SELECT (user_id, account_id) ON TABLE public.account_memberships "
        f"TO {resolver_role}"
    )
    op.execute(
        "GRANT SELECT (token, account_id) ON TABLE public.account_invites "
        f"TO {resolver_role}"
    )
    op.execute(
        "ALTER FUNCTION public.app_account_id_for_user(uuid) "
        f"OWNER TO {resolver_role}"
    )
    op.execute(
        "ALTER FUNCTION public.app_account_id_for_invite_token(text) "
        f"OWNER TO {resolver_role}"
    )
    op.execute("REVOKE ALL ON FUNCTION public.app_account_id_for_user(uuid) FROM PUBLIC")
    op.execute(
        "REVOKE ALL ON FUNCTION public.app_account_id_for_invite_token(text) FROM PUBLIC"
    )
    op.execute(
        f"GRANT EXECUTE ON FUNCTION public.app_account_id_for_user(uuid) TO {runtime_role}"
    )
    op.execute(
        f"GRANT EXECUTE ON FUNCTION public.app_account_id_for_invite_token(text) TO {runtime_role}"
    )


def downgrade() -> None:
    """Удалить resolver-функции."""
    op.execute("DROP FUNCTION public.app_account_id_for_invite_token(text)")
    op.execute("DROP FUNCTION public.app_account_id_for_user(uuid)")
    op.execute(
        "REVOKE SELECT (token, account_id) ON TABLE public.account_invites "
        "FROM landlords_rls_resolver"
    )
    op.execute(
        "REVOKE SELECT (user_id, account_id) ON TABLE public.account_memberships "
        "FROM landlords_rls_resolver"
    )
