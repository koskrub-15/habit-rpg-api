from datetime import datetime
from this import d

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import registry

mapper_registry = registry()


@mapper_registry.as_declarative_base()
class Base:
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text, nullable=True)


@mapper_registry.as_declarative_base()
class SimpleBase:
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BaseSchemaCreate(BaseModel):
    name: str
    description: str


class SimpleBaseSchemaCreate(BaseModel):
    name: str


class BaseSchemaResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
