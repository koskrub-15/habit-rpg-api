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
