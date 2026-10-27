# INSTALL_MODE=offline — COPY готового .venv (сборка без PyPI)
# INSTALL_MODE=online  — pip install -r requirements.lock (CI / чистая машина)
# Без "# syntax=docker/dockerfile:1" — иначе build тянет frontend с Docker Hub.
ARG INSTALL_MODE=offline

FROM python:3.12-slim AS base

WORKDIR /app

RUN useradd -m -u 1000 appuser

# --- offline: пакеты из локального .venv ---
FROM base AS deps-offline
COPY .venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages/

# --- online: установка из requirements.lock ---
FROM base AS deps-online
COPY backend/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock

# Выбор режима: --build-arg INSTALL_MODE=offline|online
FROM deps-${INSTALL_MODE} AS deps

FROM base AS final
ARG INSTALL_MODE=offline

# Переносим site-packages / установленные пакеты из deps-stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY backend/app/ /app/app/
COPY backend/worker.py /app/
COPY backend/alembic.ini /app/
COPY backend/alembic/ /app/alembic/
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" || exit 1

EXPOSE 8000

# Entrypoint с миграциями включается только у сервиса api (RUN_MIGRATIONS=1).
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
