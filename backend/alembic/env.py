"""
Конфигурация Alembic для автообнаружения моделей и генерации миграций.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.models.base import Base

# Alembic Config объект
config = context.config

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подставляем реальный URL базы данных из settings
config.set_main_option("sqlalchemy.url", settings.MIGRATION_DATABASE_URL)

# Метаданные для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запустить миграции в офлайн-режиме (генерация SQL без БД)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запустить миграции в онлайн-режиме (подключение к реальной БД)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Alembic сам вызовет нужную функцию. Не вызываем их здесь.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()