from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.schemas.achievement import AchievementResponseShort
from apps.schemas.habit import HabitResponseShort
from apps.schemas.item import ItemResponseShort
from apps.schemas.notification import (
    NotificationResponse,
    UserNotificationPreferenceResponse,
)
from apps.schemas.task import TaskResponseShort


class UserCreate(SimpleBaseSchemaCreate):
    email: str
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    health_points: Optional[int] = None
    experience: Optional[int] = None
    gold: Optional[int] = None


class UserResponseShort(BaseSchemaResponse):
    email: str


class UserResponse(BaseSchemaResponse):
    health_points: int
    experience: int
    gold: int
    achievements: List["AchievementResponseShort"] = []
    equipped_items: List["ItemResponseShort"] = []
    inventory_items: List["ItemResponseShort"] = []
    tasks: List["TaskResponseShort"] = []
    habits: List["HabitResponseShort"] = []
    notifications: List["NotificationResponse"] = []
    notification_preferences: List["UserNotificationPreferenceResponse"] = []
