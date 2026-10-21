"""Найти и при необходимости удалить файлы без metadata в PostgreSQL."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings
from app.db.models.document_model import DocumentModel
from app.db.session import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help="Удалить файлы без metadata в PostgreSQL (по умолчанию только отчёт)",
    )
    args = parser.parse_args()

    storage_root = Path(settings.DOCUMENTS_STORAGE_DIR).resolve()
    if not storage_root.is_dir():
        print("Каталог документов не существует.")
        return 0

    with SessionLocal() as session:
        registered_paths = {
            Path(path).resolve()
            for (path,) in session.query(DocumentModel.file_path).all()
            if path
        }

    orphans: list[Path] = []
    for candidate in storage_root.rglob("*"):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if storage_root not in resolved.parents or resolved in registered_paths:
            continue
        orphans.append(candidate)

    action = "Удалён" if args.delete_orphans else "Orphan"
    for candidate in orphans:
        print(f"{action}: {candidate.relative_to(storage_root)}")
        if args.delete_orphans:
            candidate.unlink()
    print(f"Количество orphan-файлов: {len(orphans)}")
    if not args.delete_orphans:
        print("Режим просмотра. Передайте --delete-orphans для удаления.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
