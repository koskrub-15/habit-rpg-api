from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.notification import NotificationType


class NotificationCreate(BaseSchemaCreate):
    user_id: int
    notification_type: NotificationType
    message: str


class NotificationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[int] = None
    notification_type: Optional[NotificationType] = None
    message: Optional[str] = None


class NotificationResponse(BaseSchemaResponse):
    description: str
    user_id: int
    notification_type: NotificationType
    message: str
    user: "UserResponseShort"


class UserNotificationPreferenceCreate(SimpleBaseSchemaCreate):
    user_id: int
    notification_type: NotificationType
    is_enabled: Optional[bool] = False


class UserNotificationPreferenceUpdate(BaseModel):
    name: Optional[str] = None
    user_id: Optional[int] = None
    notification_type: Optional[NotificationType] = None
    is_enabled: Optional[bool] = None


class UserNotificationPreferenceResponse(BaseSchemaResponse):
    user_id: int
    notification_type: NotificationType
    is_enabled: bool
    user: "UserResponseShort"
