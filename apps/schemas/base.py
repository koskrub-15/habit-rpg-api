from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SimpleBaseSchemaCreate(BaseModel):
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class BaseSchemaResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
