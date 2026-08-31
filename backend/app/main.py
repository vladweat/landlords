from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_middleware import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError


def _init_sentry() -> None:
    """Инициализировать Sentry, если задан SENTRY_DSN."""
    if not settings.SENTRY_DSN:
        return

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1 if settings.APP_ENV == "production" else 0.0,
    )


def create_app() -> FastAPI:
    """
    Создать и сконфигурировать экземпляр FastAPI.

    Returns:
        Сконфигурированное приложение FastAPI.
    """
    _init_sentry()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Middleware
    app.add_middleware(LoggingMiddleware)
    
    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )
    
    # Обработчик ошибок валидации
    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "message": "Validation error",
                "details": exc.errors(),
            },
        )

    # Глобальный обработчик кастомных исключений
    @app.exception_handler(AppException)
    def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Обработать кастомное исключение приложения."""
        logger.warning(
            f"Application exception: {exc.message}",
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
            },
        )

    # Обработчик необработанных исключений
    @app.exception_handler(Exception)
    def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Обработать неожиданное исключение."""
        logger.exception("Unhandled exception: {}", str(exc), path=request.url.path)
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error",
            },
        )

    # Healthcheck
    @app.get("/health", tags=["System"])
    def healthcheck() -> dict[str, str]:
        """Проверка работоспособности сервиса."""
        return {"status": "ok"}

    from app.api.v1.routes.auth import router as auth_router
    from app.api.v1.routes.properties import router as properties_router
    from app.api.v1.routes.tenants import router as tenants_router
    from app.api.v1.routes.contracts import router as contracts_router
    from app.api.v1.routes.charges import router as charges_router
    from app.api.v1.routes.payments import router as payments_router
    from app.api.v1.routes.dashboard import router as dashboard_router
    from app.api.v1.routes.reminders import router as reminders_router
    from app.api.v1.routes.feedback import router as feedback_router

    app.include_router(auth_router)
    app.include_router(properties_router)
    app.include_router(tenants_router)
    app.include_router(contracts_router)
    app.include_router(charges_router)
    app.include_router(payments_router)
    app.include_router(dashboard_router)
    app.include_router(reminders_router)
    app.include_router(feedback_router)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )