from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from apps.models.activity_log import ActivityType


class ActivityLogBase(BaseModel):
    activity_type: ActivityType
    description: Optional[str] = None
    task_id: Optional[int] = None
    habit_id: Optional[int] = None
    item_id: Optional[int] = None
    achievement_id: Optional[int] = None


class ActivityLogCreate(ActivityLogBase):
    user_id: int


class ActivityLogUpdate(ActivityLogBase):
    pass


class ActivityLogResponse(ActivityLogBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
