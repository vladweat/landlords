"""Idempotently provision the least-privilege application database role."""

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
