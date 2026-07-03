from fastapi import Depends

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.notification import (
    notification_crud,
    user_notification_preference_crud,
)
from apps.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
    UserNotificationPreferenceCreate,
    UserNotificationPreferenceResponse,
    UserNotificationPreferenceUpdate,
)

notification_factory = RouterFactory(
    crud=notification_crud,
    create_schema=NotificationCreate,
    update_schema=NotificationUpdate,
    response_schema=NotificationResponse,
    response_short_schema=NotificationResponse,  # No short version defined
    resource_name="notification",
    resource_name_plural="notifications",
    tag="Notifications",
    prefix="/notifications",
    current_user_dependency=Depends(get_current_user),
)

user_notification_preference_factory = RouterFactory(
    crud=user_notification_preference_crud,
    create_schema=UserNotificationPreferenceCreate,
    update_schema=UserNotificationPreferenceUpdate,
    response_schema=UserNotificationPreferenceResponse,
    response_short_schema=UserNotificationPreferenceResponse,  # No short version defined
    resource_name="user_notification_preference",
    resource_name_plural="user_notification_preferences",
    tag="Notifications",
    prefix="/user_notification_preferences",
    current_user_dependency=Depends(get_current_user),
)

notification_router = notification_factory.create_router()
user_notification_preference_router = (
    user_notification_preference_factory.create_router()
)
