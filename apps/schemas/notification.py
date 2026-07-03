from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from apps.models.notification import NotificationType
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate


class NotificationCreate(SimpleBaseSchemaCreate):
    user_id: Optional[int] = None
    notification_type: NotificationType
    message: str


class NotificationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    notification_type: Optional[NotificationType] = None
    message: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseSchemaResponse):
    user_id: int
    notification_type: NotificationType
    message: str


class UserNotificationPreferenceCreate(SimpleBaseSchemaCreate):
    user_id: Optional[int] = None
    notification_type: NotificationType
    is_enabled: bool = False


class UserNotificationPreferenceUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)


class UserNotificationPreferenceResponse(BaseSchemaResponse):
    user_id: int
    notification_type: NotificationType
    is_enabled: bool
