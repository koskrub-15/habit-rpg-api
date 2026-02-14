from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse
from apps.models.habit import HabitStatus, HabitType
from apps.models.task import Size


class HabitCreate(BaseSchemaCreate):
    habit_type: Optional[HabitType] = HabitType.NEUTRAL
    habit_size: Optional[Size] = Size.SMALL
    user_id: int


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[HabitStatus] = None
    habit_size: Optional[Size] = None


class HabitResponseShort(BaseSchemaResponse):
    user_id: int
    description: str
    habit_size: Size
    status: HabitStatus


class HabitResponse(HabitResponseShort):
    streak: int
    overfullfillment: int
    user: "UserResponseShort"
