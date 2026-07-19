from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from apps.models.user import SlotType
from apps.schemas.achievement import AchievementResponseShort
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.schemas.habit import HabitResponseShort
from apps.schemas.item import ItemResponseShort
from apps.schemas.notification import (
    NotificationResponse,
    UserNotificationPreferenceResponse,
)
from apps.schemas.task import TaskResponse


class UserCreate(SimpleBaseSchemaCreate):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    health_points: Optional[int] = None
    experience: Optional[int] = None
    gold: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class UserResponseShort(BaseSchemaResponse):
    email: str


class UserResponse(UserResponseShort):
    health_points: int = 100
    experience: int = 0
    gold: int = 0
    is_superuser: bool = False
    last_cron_at: Optional[datetime] = None
    habits: List[HabitResponseShort] = []
    tasks: List[TaskResponse] = []
    achievements: List[AchievementResponseShort] = []
    notifications: List[NotificationResponse] = []
    notification_preferences: List[UserNotificationPreferenceResponse] = []
    equipped_items: List[ItemResponseShort] = []
    inventory_items: List[ItemResponseShort] = []


class CompleteActivityRequest(BaseModel):
    activity_type: str
    activity_id: int
    performed: bool = True


class CompleteActivityResponse(BaseModel):
    activity_type: str
    activity_name: str
    exp_gained: int
    gold_gained: int
    health_change: int
    new_level: int
    current_health: int
    streak: Optional[str] = None
    died: bool = False
    model_config = ConfigDict(from_attributes=True)


class SubTaskCompleteResponse(BaseModel):
    sub_task_id: int
    task_id: int
    task_completed: bool
    task_reward: Optional[CompleteActivityResponse] = None
    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    name: str
    level: int
    experience: int
    model_config = ConfigDict(from_attributes=True)


class DailyCronResponse(BaseModel):
    ran: bool
    missed_dailies: int
    health_lost: int
    current_health: int
    died: bool = False
    model_config = ConfigDict(from_attributes=True)


class UserStatsResponse(BaseModel):
    level: int
    health_points: int
    attack: int
    defense: int
    pet_power: int
    model_config = ConfigDict(from_attributes=True)


class EquipItemRequest(BaseModel):
    item_id: int
    slot: SlotType


class UnequipItemRequest(BaseModel):
    slot: SlotType


class EquippedItemResponse(BaseModel):
    id: Optional[int] = None
    user_id: int
    item_id: int
    slot: SlotType
    model_config = ConfigDict(from_attributes=True)


class InventoryItemResponse(BaseModel):
    id: Optional[int] = None
    user_id: int
    item_id: int
    quantity: int
    model_config = ConfigDict(from_attributes=True)


class UpdateInventoryRequest(BaseModel):
    item_id: int
    quantity: int = 1
