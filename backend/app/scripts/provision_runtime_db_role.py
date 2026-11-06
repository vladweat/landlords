"""Повторяемая настройка runtime роли с минимальными правами."""

from pathlib import Path

from app.core.config import settings
from psycopg2 import connect, sql
from sqlalchemy.engine import make_url


def _psycopg2_dsn(url: str) -> str:
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def provision_runtime_role(database_name: str | None = None) -> None:
    owner = settings.MIGRATION_DB_USER
    password = (
        settings.MIGRATION_DB_PASSWORD.get_secret_value()
        if settings.MIGRATION_DB_PASSWORD is not None
        else None
    )
    runtime = settings.DB_USER
    database_name = database_name or settings.DB_NAME
    if not owner or not password:
        raise RuntimeError("Migration database credentials are required for role provisioning.")
    if owner == runtime:
        raise RuntimeError("DB_USER must differ from MIGRATION_DB_USER.")

    owner_url = make_url(settings.MIGRATION_DATABASE_URL).set(database=database_name)
    with connect(_psycopg2_dsn(owner_url.render_as_string(hide_password=False))) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            if not cursor.fetchone()[0]:
                raise RuntimeError(
                    "Migration database role must be a superuser to provision the "
                    "dedicated PostgreSQL RLS resolver role."
                )

            exporter_password_file = settings.POSTGRES_EXPORTER_PASSWORD_FILE
            if exporter_password_file:
                try:
                    exporter_password = Path(exporter_password_file).read_text(
                        encoding="utf-8"
                    ).strip()
                except OSError:
                    raise RuntimeError(
                        "Unable to read PostgreSQL exporter password file."
                    ) from None
                if not exporter_password:
                    raise RuntimeError("PostgreSQL exporter password file is empty.")

                exporter = settings.POSTGRES_EXPORTER_USER
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (exporter,))
                exporter_exists = cursor.fetchone() is not None
                exporter_statement = sql.SQL(
                    "ALTER ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE INHERIT NOREPLICATION NOBYPASSRLS"
                    if exporter_exists
                    else "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE INHERIT NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(exporter), sql.Literal(exporter_password))
                cursor.execute(exporter_statement)
                cursor.execute(
                    sql.SQL("REVOKE ALL PRIVILEGES ON DATABASE {} FROM {}").format(
                        sql.Identifier(database_name), sql.Identifier(exporter)
                    )
                )
                cursor.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(database_name), sql.Identifier(exporter)
                    )
                )
                cursor.execute(
                    sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(
                        sql.Identifier(exporter)
                    )
                )
                cursor.execute(
                    sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(
                        sql.Identifier(exporter)
                    )
                )
                cursor.execute(
                    sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}").format(
                        sql.Identifier(exporter)
                    )
                )
                cursor.execute(
                    sql.SQL("REVOKE pg_read_all_data, pg_write_all_data FROM {}").format(
                        sql.Identifier(exporter)
                    )
                )
                cursor.execute(
                    sql.SQL("GRANT pg_monitor TO {}").format(sql.Identifier(exporter))
                )

            cursor.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", ("landlords_rls_resolver",)
            )
            resolver_exists = cursor.fetchone() is not None
            resolver_statement = sql.SQL(
                "ALTER ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION BYPASSRLS"
                if resolver_exists
                else "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION BYPASSRLS"
            ).format(sql.Identifier("landlords_rls_resolver"))
            cursor.execute(resolver_statement)

            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (runtime,))
            role_exists = cursor.fetchone() is not None
            role_statement = sql.SQL(
                "ALTER ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                if role_exists
                else "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
            ).format(sql.Identifier(runtime), sql.Literal(settings.DB_PASSWORD))
            cursor.execute(role_statement)
            cursor.execute(
                sql.SQL("REVOKE {} FROM {}").format(
                    sql.Identifier("landlords_rls_resolver"), sql.Identifier(runtime)
                )
            )
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(runtime)
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                    sql.Identifier(runtime)
                )
            )
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}"
                ).format(sql.Identifier(runtime))
            )
            cursor.execute(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = ANY(%s)",
                (
                    [
                        "payment_receipts",
                        "payment_receipt_events",
                        "payment_allocation_targets",
                        "payment_allocation_events",
                    ],
                ),
            )
            for (table_name,) in cursor.fetchall():
                cursor.execute(
                    sql.SQL("REVOKE UPDATE, DELETE ON TABLE {} FROM {}").format(
                        sql.Identifier(table_name), sql.Identifier(runtime)
                    )
                )
            cursor.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}"
                ).format(sql.Identifier(runtime))
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(sql.Identifier(owner), sql.Identifier(runtime))
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}"
                ).format(sql.Identifier(owner), sql.Identifier(runtime))
            )


def main() -> None:
    provision_runtime_role()
    print("Runtime database role is ready.")


if __name__ == "__main__":
    main()
