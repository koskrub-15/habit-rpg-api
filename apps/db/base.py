from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import registry

mapper_registry = registry()

_LegacyBase = mapper_registry.generate_base()


class MinimalBase(_LegacyBase):  # type: ignore[misc, valid-type]
    """Base for models that don't need name/description (junction tables, logs, etc.)."""

    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SimpleBase(MinimalBase):
    __abstract__ = True
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)


class Base(SimpleBase):
    __abstract__ = True
