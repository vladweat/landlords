from http import HTTPStatus

class AppException(Exception):
    """Базовое исключение приложения"""
    
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    message: str = "Internal server error"
    
    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)
        
class NotFoundError(AppException):
    """Ресурс не найден."""

    status_code: int = HTTPStatus.NOT_FOUND
    message: str = "Resource not found"


class ConflictError(AppException):
    """Конфликт данных (например, дубликат)."""

    status_code: int = HTTPStatus.CONFLICT
    message: str = "Resource already exists"


class ValidationError(AppException):
    """Ошибка валидации бизнес-правил."""

    status_code: int = HTTPStatus.UNPROCESSABLE_ENTITY
    message: str = "Validation error"


class UnauthorizedError(AppException):
    """Ошибка аутентификации."""

    status_code: int = HTTPStatus.UNAUTHORIZED
    message: str = "Authentication required"


class ForbiddenError(AppException):
    """Ошибка авторизации."""

    status_code: int = HTTPStatus.FORBIDDEN
    message: str = "Access denied"


class GoneError(AppException):
    """Ресурс больше недоступен (истёк, отозван, уже использован)."""

    status_code: int = HTTPStatus.GONE
    message: str = "Resource no longer available"


class ServiceUnavailableError(AppException):
    """Внешний сервис недоступен."""

    status_code: int = HTTPStatus.SERVICE_UNAVAILABLE
    message: str = "Service temporarily unavailable"