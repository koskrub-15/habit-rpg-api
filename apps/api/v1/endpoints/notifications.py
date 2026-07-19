from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.notification import (
    notification_crud,
    user_notification_preference_crud,
)
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
    UnreadCountResponse,
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
    owner_field="user_id",
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
    owner_field="user_id",
)

notification_router = notification_factory.create_router()
user_notification_preference_router = (
    user_notification_preference_factory.create_router()
)


@notification_router.get(
    "/unread/count",
    response_model=UnreadCountResponse,
    summary="Count the current user's unread notifications",
)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return how many notifications the current user has not read yet."""
    count = await notification_crud.count_unread(db, current_user.id)
    return UnreadCountResponse(unread=count)


@notification_router.post(
    "/read-all",
    response_model=UnreadCountResponse,
    summary="Mark all of the current user's notifications read",
)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark every unread notification read; returns the remaining unread count (0)."""
    await notification_crud.mark_all_read(db, current_user.id)
    return UnreadCountResponse(unread=0)


@notification_router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a single notification read",
)
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark one of the current user's notifications read."""
    return await notification_crud.mark_read(db, notification_id, current_user.id)
