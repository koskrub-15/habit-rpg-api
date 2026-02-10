from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import registry

mapper_registry = registry()


@mapper_registry.as_declarative_base()
class Base:
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
