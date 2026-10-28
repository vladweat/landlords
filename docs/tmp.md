# Внутренние технические заметки

## Ограничения и trade-offs

- Sync SQLAlchemy упрощает транзакции, но blocking I/O занимает worker thread.
- Один общий `deps.py` и крупные services/routes увеличивают связность.
- API и Celery совместно используют модели/services, но не общий unit of work.
- Файловое хранилище требует общего volume и не поддерживает горизонтальное
  масштабирование без shared filesystem/object storage.
- Миграции автоматически выполняет API на старте; несколько одновременно
  стартующих API replicas не предусмотрены.
