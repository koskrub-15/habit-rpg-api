from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.notification import NotificationType


# --- Notification Schemas ---
class NotificationCreate(BaseSchemaCreate):
    # BaseSchemaCreate provides 'name', 'description'
    user_id: int
    notification_type: NotificationType
    message: str # 'name' from BaseSchemaCreate will likely be used as a title or short identifier

class NotificationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[int] = None
    notification_type: Optional[NotificationType] = None
    message: Optional[str] = None

class NotificationResponse(BaseSchemaResponse):
    # BaseSchemaResponse provides id, name, created_at, updated_at
    user_id: int
    notification_type: NotificationType
    message: str
    user: "UserResponseShort" # Forward reference

# --- UserNotificationPreference Schemas ---
class UserNotificationPreferenceCreate(SimpleBaseSchemaCreate): # Inherits name
    user_id: int
    notification_type: NotificationType
    is_enabled: Optional[bool] = False

class UserNotificationPreferenceUpdate(BaseModel):
    name: Optional[str] = None
    user_id: Optional[int] = None
    notification_type: Optional[NotificationType] = None
    is_enabled: Optional[bool] = None

class UserNotificationPreferenceResponse(BaseSchemaResponse):
    # BaseSchemaResponse provides id, name, created_at, updated_at
    user_id: int
    notification_type: NotificationType
    is_enabled: bool
    user: "UserResponseShort" # Forward reference
