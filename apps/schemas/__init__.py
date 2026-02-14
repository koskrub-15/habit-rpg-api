from apps.schemas.achievement import (
    AchievementResponse,
    AchievementResponseFull,
    AchievementResponseShort,
    RewardResponse,
    RewardResponseShort,
)
from apps.schemas.habit import (
    HabitResponse,
    HabitResponseShort,
)
from apps.schemas.item import (
    ItemResponse,
    ItemResponseFull,
    ItemResponseShort,
)
from apps.schemas.notification import (
    NotificationResponse,
    UserNotificationPreferenceResponse,
)
from apps.schemas.store_rotation import (
    ShopItemResponse,
    ShopItemResponseShort,
    ShopRotationItemResponse,
    ShopRotationItemResponseShort,
    ShopRotationResponse,
    ShopRotationResponseShort,
)
from apps.schemas.task import (
    SubTaskResponse,
    SubTaskResponseShort,
    TaskResponse,
    TaskResponseShort,
)
from apps.schemas.user import (
    UserResponse,
    UserResponseShort,
)

UserResponse.model_rebuild()
AchievementResponse.model_rebuild()
AchievementResponseFull.model_rebuild()
RewardResponse.model_rebuild()
HabitResponse.model_rebuild()
ItemResponse.model_rebuild()
ItemResponseFull.model_rebuild()
NotificationResponse.model_rebuild()
UserNotificationPreferenceResponse.model_rebuild()
ShopItemResponse.model_rebuild()
ShopRotationResponse.model_rebuild()
ShopRotationItemResponse.model_rebuild()
TaskResponse.model_rebuild()
SubTaskResponse.model_rebuild()
