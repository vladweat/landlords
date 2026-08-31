"""Базовая модель SQLAlchemy и миксин с временными метками."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class TimestampMixin:
    """Миксин с created_at и updated_at для всех моделей."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""