from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.notification import NotificationType

if TYPE_CHECKING:
    from apps.schemas.user import UserResponseShort


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
