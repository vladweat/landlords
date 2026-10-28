from sqlalchemy import text


def test_runtime_role_is_not_superuser_or_table_owner(test_engine) -> None:
    with test_engine.connect() as connection:
        role = connection.execute(
            text(
                """
                SELECT r.rolsuper, r.rolbypassrls, r.rolcreaterole,
                       EXISTS (
                           SELECT 1 FROM pg_tables t
                           WHERE t.schemaname = 'public'
                             AND t.tableowner = current_user
                       )
                FROM pg_roles r
                WHERE r.rolname = current_user
                """
            )
        ).one()

    assert role == (False, False, False, False)
