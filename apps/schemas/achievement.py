from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate


class AchievementCreate(SimpleBaseSchemaCreate):
    condition_type: str
    condition_value: int


class AchievementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition_type: Optional[str] = None
    condition_value: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class AchievementResponseShort(BaseSchemaResponse):
    condition_type: str
    condition_value: int


class AchievementResponse(AchievementResponseShort):
    pass


class RewardCreate(SimpleBaseSchemaCreate):
    gold: int
    experience: int
    health_points: int


class RewardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    gold: Optional[int] = None
    experience: Optional[int] = None
    health_points: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class RewardResponseShort(BaseSchemaResponse):
    gold: int
    experience: int
    health_points: int


class RewardResponse(RewardResponseShort):
    pass
