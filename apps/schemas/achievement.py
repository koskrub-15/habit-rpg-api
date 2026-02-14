from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse, SimpleBaseSchemaCreate


class AchievementCreate(BaseSchemaCreate):
    condition_type: str
    condition_value: int


class AchievementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition_type: Optional[str] = None
    condition_value: Optional[int] = None


class AchievementResponseShort(BaseSchemaResponse):
    description: str


class AchievementResponse(AchievementResponseShort):
    condition_type: str
    condition_value: int
    rewards: List["RewardResponseShort"] = []


class AchievementResponseFull(AchievementResponse):
    users: List["UserResponseShort"] = []


class RewardCreate(SimpleBaseSchemaCreate):
    gold: int
    experience: int
    health_points: int


class RewardUpdate(BaseModel):
    name: Optional[str] = None
    gold: Optional[int] = None
    experience: Optional[int] = None
    health_points: Optional[int] = None


class RewardResponseShort(BaseSchemaResponse):
    gold: int
    experience: int
    health_points: int


class RewardResponse(RewardResponseShort):
    items: List["ItemResponseShort"] = []
    achievements: List["AchievementResponseShort"] = []
