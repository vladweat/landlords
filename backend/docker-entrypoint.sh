#!/bin/sh
set -e
# Миграции только у API (RUN_MIGRATIONS=1). Worker/beat этот скрипт не вызывают.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running alembic upgrade head..."
  python -m alembic upgrade head
fi
exec "$@"
