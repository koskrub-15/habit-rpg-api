from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from apps.models.activity_log import ActivityType


class ActivityLogCreate(BaseModel):
    user_id: int
    activity_type: ActivityType
    description: Optional[str] = None
    task_id: Optional[int] = None
    habit_id: Optional[int] = None
    item_id: Optional[int] = None
    achievement_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class ActivityLogUpdate(BaseModel):
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ActivityLogResponse(BaseModel):
    id: int
    user_id: int
    activity_type: ActivityType
    description: Optional[str] = None
    task_id: Optional[int] = None
    habit_id: Optional[int] = None
    item_id: Optional[int] = None
    achievement_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
