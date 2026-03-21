from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.user import SlotType
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


class UserResponse(UserResponseShort):
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


class EquippedItemResponse(BaseSchemaResponse):
    user_id: int
    item_id: int
    slot: SlotType


class InventoryItemResponse(BaseSchemaResponse):
    user_id: int
    item_id: int
    quantity: int


class CompleteActivityRequest(BaseModel):
    """input data for \"complete_activity\" """

    activity_type: str
    activity_id: int
    performed: bool = True


class CompleteActivityResponse(BaseModel):
    """result of \"complete_activity\" operation"""

    activity_type: str
    activity_name: str
    exp_gained: int
    gold_gained: int
    health_change: int
    new_level: int
    current_health: int
    streak: Optional[str] = None


class UpdateInventoryRequest(BaseModel):
    item_id: int
    quantity: int


class EquipItemRequest(BaseModel):
    item_id: int
    slot: SlotType

class UnequipItemRequest(BaseModel):
    slot: SlotType
