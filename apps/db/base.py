from datetime import datetime, timezone

from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import registry

mapper_registry = registry()


@mapper_registry.as_declarative_base()
class Base:
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    description = Column(Text, nullable=True)


@mapper_registry.as_declarative_base()
class SimpleBase:
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


@mapper_registry.as_declarative_base()
class MinimalBase:
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BaseSchemaCreate(BaseModel):
    name: str
    description: str


class SimpleBaseSchemaCreate(BaseModel):
    name: str


class BaseSchemaResponse(BaseModel):
    id: int
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
