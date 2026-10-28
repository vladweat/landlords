import pytest
from app.scripts.provision_runtime_db_role import _psycopg2_dsn


def test_psycopg2_dsn_converts_sqlalchemy_driver_url() -> None:
    assert _psycopg2_dsn(
        "postgresql+psycopg2://migration:secret@db:5432/landlords"
    ) == "postgresql://migration:secret@db:5432/landlords"
