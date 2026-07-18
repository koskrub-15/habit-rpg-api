from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from apps.models.habit import HabitStatus, HabitType
from apps.models.task import Size
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate


class HabitCreate(SimpleBaseSchemaCreate):
    user_id: Optional[int] = None
    habit_type: HabitType = HabitType.NEUTRAL
    habit_size: Size = Size.SMALL
    status: HabitStatus = HabitStatus.TODO
    streak: int = 0
    overfulfillment: int = 0


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    habit_type: Optional[HabitType] = None
    habit_size: Optional[Size] = None
    status: Optional[HabitStatus] = None
    streak: Optional[int] = None
    overfulfillment: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class HabitResponseShort(BaseSchemaResponse):
    user_id: int
    habit_type: HabitType
    habit_size: Size
    status: HabitStatus
    streak: int = 0
    overfulfillment: int = 0
    last_completed_at: Optional[datetime] = None


class HabitResponse(HabitResponseShort):
    pass
