import time
import uuid

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware, добавляющий request_id и логирующий запросы/ответы.

    - Генерирует request_id, если его нет в заголовке X-Request-ID.
    - Логирует метод, путь, статус и время выполнения.
    - Добавляет request_id в заголовки ответа.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Обработать запрос, добавив request_id и логирование."""
        # Получаем или генерируем request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Добавляем request_id в контекст logger
        with logger.contextualize(request_id=request_id):
            start_time = time.monotonic()

            # Логируем входящий запрос
            logger.info(
                "Incoming request",
                method=request.method,
                path=request.url.path,
                query=str(request.query_params),
                client_ip=request.client.host if request.client else "unknown",
            )

            # Выполняем запрос
            response: Response = await call_next(request)

            # Вычисляем время выполнения
            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Логируем ответ
            logger.info(
                "Outgoing response",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                elapsed_ms=round(elapsed_ms, 2),
            )

            # Добавляем request_id в заголовки ответа
            response.headers["X-Request-ID"] = request_id

            return response