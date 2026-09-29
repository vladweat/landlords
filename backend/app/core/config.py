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
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = True
    
    # ==================== Security ====================
    
    SECRET_KEY: str = "change-me-in-production-change-me"
    SENTRY_DSN: str | None = None
    
    # ==================== Frontend / Email ====================
    # Базовый URL фронтенда — используется для формирования ссылок в письмах (reset password).
    FRONTEND_URL: str = "http://localhost:3000"

    # SMTP (опционально). Если не задано, письма пишутся в storage/emails/ для dev.
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    # ==================== База данных ====================
    
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "landlords_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False  # SQL-логирование (только для разработки)
    
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    # ==================== Redis ====================
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ==================== Celery ====================
    
    CELERY_TASK_DEFAULT_QUEUE: str = "default"
    CELERY_TASK_SOFT_TIME_LIMIT: int = 300  # 5 минут
    CELERY_TASK_TIME_LIMIT: int = 600  # 10 минут
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1000  # Перезапуск воркера после N задач
    
    # ==================== Logging ====================
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
settings = Settings()
# Ensure SECRET_KEY is explicitly set in production
if settings.APP_ENV == "production" and (
    not settings.SECRET_KEY or settings.SECRET_KEY == "change-me-in-production-change-me"
):
    raise RuntimeError(
        "SECRET_KEY must be set in production. Set SECRET_KEY in the environment and restart."
    )