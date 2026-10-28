import os
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из .env файла.

    Все переменные имеют префикс APP_ для избежания конфликтов
    с системными переменными окружения.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # ==================== Приложение ====================
    
    APP_NAME: str = "FastAPI DDD Service"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    # Публичный POST /v1/auth/register. Для портфолио/прода — false; CLI seed не зависит от флага.
    ALLOW_PUBLIC_REGISTRATION: bool = True
    
    # ==================== Security ====================
    
    SECRET_KEY: str = "change-me-in-production-change-me"
    SENTRY_DSN: str | None = None
    
    # ==================== Frontend / Email ====================
    # Базовый URL фронтенда — используется для формирования ссылок в письмах (reset password).
    FRONTEND_URL: str = "http://localhost:3000"
    SUPPORT_EMAIL: str = "hello@landlords.ru"

    # Почта: SMTP вручную и/или Resend API key (тогда smtp.resend.com).
    # SMTP_TLS_MODE=none разрешён только вне production.
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_TLS_MODE: Literal["starttls", "ssl", "none"] = "starttls"
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    RESEND_API_KEY: str | None = None

    # ==================== Ops / алерты ====================
    # Файл статуса инцидентов (правка без редеплоя).
    STATUS_INCIDENTS_PATH: str = "/app/storage/status/incidents.json"
    OPS_DISK_MIN_FREE_MB: int = 500
    OPS_BEAT_STALE_HOURS: int = 26
    DOCUMENTS_STORAGE_DIR: str = "/app/storage/documents"

    # ==================== ЮKassa (SaaS billing) ====================
    # Демо-магазин: ключ начинается с test_. Без ключей checkout недоступен.
    YOOKASSA_SHOP_ID: str | None = None
    YOOKASSA_SECRET_KEY: str | None = None
    YOOKASSA_RETURN_URL: str | None = None
    BILLING_PRO_PRICE_RUB: int = 990
    BILLING_GRACE_DAYS: int = 3

    @field_validator(
        "YOOKASSA_SHOP_ID",
        "YOOKASSA_SECRET_KEY",
        "YOOKASSA_RETURN_URL",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("BILLING_PRO_PRICE_RUB", "BILLING_GRACE_DAYS", mode="before")
    @classmethod
    def _empty_int_to_default(cls, value: object, info) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return 990 if info.field_name == "BILLING_PRO_PRICE_RUB" else 3
        return value

    @property
    def billing_enabled(self) -> bool:
        """ЮKassa настроена (есть shop id и secret)."""
        return bool(
            self.YOOKASSA_SHOP_ID
            and self.YOOKASSA_SECRET_KEY
            and str(self.YOOKASSA_SECRET_KEY).strip()
        )

    @property
    def yookassa_return_url(self) -> str:
        """URL возврата после оплаты."""
        if self.YOOKASSA_RETURN_URL:
            return self.YOOKASSA_RETURN_URL
        return f"{self.FRONTEND_URL.rstrip('/')}/settings?billing=return"

    # ==================== База данных ====================
    
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    MIGRATION_DB_USER: str | None = None
    MIGRATION_DB_PASSWORD: SecretStr | None = None
    DB_NAME: str = "landlords_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False  # SQL-логирование (только для разработки)
    
    
    def _database_url(self, user: str, password: str) -> str:
        return (
            f"postgresql+psycopg2://{quote(user, safe='')}:{quote(password, safe='')}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL(self) -> str:
        """Подключение с минимальными runtime правами."""
        return self._database_url(self.DB_USER, self.DB_PASSWORD)

    @property
    def MIGRATION_DATABASE_URL(self) -> str:
        """Подключение для Alembic и одноразового DB role bootstrap."""
        user = self.MIGRATION_DB_USER
        password = (
            self.MIGRATION_DB_PASSWORD.get_secret_value()
            if self.MIGRATION_DB_PASSWORD is not None
            else None
        )
        if bool(user) != bool(password):
            raise RuntimeError(
                "MIGRATION_DB_USER and MIGRATION_DB_PASSWORD must be set together."
            )
        if not user or not password:
            if self.APP_ENV == "production":
                raise RuntimeError(
                    "MIGRATION_DB_USER and MIGRATION_DB_PASSWORD are required for production migrations."
                )
            return self.DATABASE_URL
        if self.APP_ENV == "production" and user == self.DB_USER:
            raise RuntimeError(
                "MIGRATION_DB_USER must differ from DB_USER in production."
            )
        return self._database_url(user, password)
    
    # ==================== Redis ====================
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_KEY_PREFIX: str = "landlords:"
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD_FILE: str | None = None
    REDIS_PASSWORD: SecretStr | None = None  # локальная совместимость; production uses a file

    def _get_redis_password(self) -> str | None:
        if self.REDIS_PASSWORD_FILE:
            try:
                password = Path(self.REDIS_PASSWORD_FILE).read_text(encoding="utf-8").strip()
            except OSError:
                raise RuntimeError("Unable to read Redis password file") from None
            if not password:
                raise RuntimeError("Redis password file is empty")
            return password
        if self.REDIS_PASSWORD is not None:
            return self.REDIS_PASSWORD.get_secret_value()
        return None
    
    @property
    def REDIS_URL(self) -> str:
        password = self._get_redis_password()
        if self.REDIS_USERNAME and not password:
            raise RuntimeError("Redis username is configured without a password")
        credentials = ""
        if password:
            if self.REDIS_USERNAME:
                credentials = f"{quote(self.REDIS_USERNAME, safe='')}:{quote(password, safe='')}@"
            else:
                credentials = f":{quote(password, safe='')}@"
        return f"redis://{credentials}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ==================== Celery ====================
    
    CELERY_TASK_DEFAULT_QUEUE: str = "default"
    CELERY_TASK_SOFT_TIME_LIMIT: int = 300  # 5 минут
    CELERY_TASK_TIME_LIMIT: int = 600  # 10 минут
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1000  # Перезапуск воркера после N задач

    # ==================== Transactional outbox ====================
    OUTBOX_RELAY_POLL_SECONDS: float = 2.0
    OUTBOX_RELAY_BATCH_SIZE: int = 50
    OUTBOX_RELAY_LEASE_SECONDS: int = 300
    OUTBOX_RELAY_MAX_ATTEMPTS: int = 12
    OUTBOX_RELAY_BASE_BACKOFF_SECONDS: float = 2.0
    OUTBOX_RELAY_MAX_BACKOFF_SECONDS: int = 300
    OUTBOX_TASK_MAX_FAILURES: int = 5
    
    # ==================== Logging ====================
    
    LOG_LEVEL: str = "INFO"
    
settings = Settings()


def _validate_production_settings(config: Settings) -> None:
    """Проверить обязательные настройки production при старте приложения."""
    if config.APP_ENV != "production":
        return
    if os.getenv("RUN_MIGRATIONS") == "1":
        _ = config.MIGRATION_DATABASE_URL
        return
    if not config.SECRET_KEY or config.SECRET_KEY == "change-me-in-production-change-me":
        raise RuntimeError(
            "SECRET_KEY must be set in production. Set SECRET_KEY in the environment and restart."
        )
    if not (config.SMTP_HOST or "").strip() and not (
        config.RESEND_API_KEY or ""
    ).strip():
        raise RuntimeError(
            "An email provider (SMTP_HOST or RESEND_API_KEY) must be configured in production."
        )
    if config.SMTP_TLS_MODE == "none":
        raise RuntimeError("SMTP_TLS_MODE=none is forbidden in production.")
    if not (config.REDIS_USERNAME or "").strip():
        raise RuntimeError("REDIS_USERNAME must be set in production.")
    if not (config.REDIS_PASSWORD_FILE or "").strip():
        raise RuntimeError("REDIS_PASSWORD_FILE must be set in production.")
    config._get_redis_password()


_validate_production_settings(settings)
