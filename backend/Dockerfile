FROM python:3.12-slim

WORKDIR /app

# Копируем пакеты Python
COPY .venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages/

# Копируем код приложения
COPY backend/app/ /app/app/
COPY backend/worker.py /app/
COPY backend/alembic.ini /app/
COPY backend/alembic/ /app/alembic/

# Создаём непривилегированного пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]