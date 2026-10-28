"""Healthcheck для процесса Celery beat."""

from __future__ import annotations

import os
from pathlib import Path


def is_celery_beat_running(
    *, proc_root: Path = Path("/proc"), current_pid: int | None = None
) -> bool:
    """Проверить, что в контейнере живёт процесс beat, а не worker."""
    current_pid = os.getpid() if current_pid is None else current_pid
    try:
        processes = proc_root.iterdir()
    except OSError:
        return False

    for process in processes:
        if not process.name.isdigit() or int(process.name) == current_pid:
            continue
        try:
            arguments = (process / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if b"worker.celery_app" in arguments and b"beat" in arguments:
            return True
    return False


def main() -> None:
    raise SystemExit(0 if is_celery_beat_running() else 1)


if __name__ == "__main__":
    main()
