from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.models.notification import Notification, UserNotificationPreference
from apps.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    UserNotificationPreferenceCreate,
    UserNotificationPreferenceUpdate,
)


class CRUDNotification(BaseCRUD[Notification, NotificationCreate, NotificationUpdate]):
    def __init__(self):
        super().__init__(model=Notification)

    async def count_unread(self, db: AsyncSession, user_id: int) -> int:
        """Number of the user's unread notifications."""
        return (
            await db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
        ).scalar_one()

    async def mark_read(
        self, db: AsyncSession, notification_id: int, user_id: int
    ) -> Notification:
        """Mark a single notification read, scoped to its owner."""
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification

    async def mark_all_read(self, db: AsyncSession, user_id: int) -> int:
        """Mark every unread notification of the user read; return how many changed."""
        result = await db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await db.commit()
        return result.rowcount or 0


class CRUDUserNotificationPreference(
    BaseCRUD[
        UserNotificationPreference,
        UserNotificationPreferenceCreate,
        UserNotificationPreferenceUpdate,
    ]
):
    def __init__(self):
        super().__init__(model=UserNotificationPreference)


notification_crud = CRUDNotification()
user_notification_preference_crud = CRUDUserNotificationPreference()
