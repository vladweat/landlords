# Устранение сбоев

## `/ready` возвращает 503

Ответ `db_unavailable` означает ошибку создания Session/`SELECT 1`;
`redis_unavailable` — ошибку `PING`.

```bash
docker compose ps
docker compose logs --since=15m api postgres redis
docker compose exec postgres pg_isready -U "${DB_USER:-postgres}"
docker compose exec redis redis-cli --user landlords_health --no-auth-warning -a '' ping
```

Проверьте, что приложение внутри Compose использует hostnames `postgres` и
`redis`, а локальный процесс — `localhost`. `/health` при этом может оставаться
200: он не проверяет зависимости.

## API не стартует

- `SECRET_KEY must be set in production`: задайте уникальный `SECRET_KEY`, не
  меняя проверку.
- Ошибка COPY `.venv`: выбран default `INSTALL_MODE=offline`; на чистой машине
  пересоберите с `INSTALL_MODE=online`.
- Alembic failure до uvicorn: entrypoint имеет `set -e`; изучите API log,
  состояние `alembic current/heads`. Не stamp-айте production DB без проверки.

## Миграции расходятся

```bash
docker compose exec api python -m alembic current
docker compose exec api python -m alembic heads
docker compose logs api
```

В норме migration chain имеет один head. Перед ручным исправлением сделайте
backup. Репозиторий не содержит автоматической schema rollback procedure.

## Celery task не выполняется

```bash
docker compose logs --since=30m celery-worker celery-beat
docker compose exec celery-worker \
  python -m celery -A worker.celery_app inspect registered
docker compose exec celery-worker \
  python -m celery -A worker.celery_app inspect active
```

Проверьте Redis, registered task name, UTC schedule и сообщения
`lock_not_acquired`. Bulk-task lock имеет TTL 900 секунд; удалять его вручную опасно,
пока другой worker действительно работает. Beat healthcheck отсутствует,
ориентируйтесь на logs и heartbeat metric.

## Письма не приходят

Проверьте `SMTP_*`/`RESEND_API_KEY`, `SMTP_FROM`, сеть и worker logs. Без
credentials non-production пишет в `storage/emails` относительно working
directory. В production SMTP failure пробрасывается и task/request падает.
Базовый Compose не монтирует `storage/emails` как host volume.

## Документ не найден

Сверьте metadata `documents.file_path`, `DOCUMENTS_STORAGE_DIR`, наличие файла
в `storage/documents` и одинаковый volume у API/worker. Восстановление только
БД без файлов оставляет битые ссылки; восстановление только файлов не
восстанавливает metadata.

## Frontend получает 401

Cookie должна называться `access_token`; в production она `Secure` и не будет
отправлена по HTTP. Проверьте same-origin URL, `Set-Cookie`, активность user и
membership. Старый localStorage token поддерживается только как миграционный
Bearer. Смена `SECRET_KEY` инвалидирует все JWT.

## 429 на login/reminders

Rate limit задаёт nginx для точных paths. Подождите окно или проверьте реальный
client IP/proxy chain. Не обходите limiter публикацией API port 8000.

## Восстановление

Команды backup/restore: [deploy.md](../deploy.md). Перед restore остановите
writers. После восстановления проверьте `/ready`, migration head, вход,
несколько документов и запланированную task. Документированная процедура в
репозитории не заменяет регулярную restore drill.
