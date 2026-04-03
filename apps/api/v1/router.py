from fastapi import APIRouter

from apps.api.v1.endpoints.achievements import achievement_router, reward_router
from apps.api.v1.endpoints.friends import router as friends_router
from apps.api.v1.endpoints.habits import router as habits_router
from apps.api.v1.endpoints.items import router as items_router
from apps.api.v1.endpoints.notifications import (
    notification_router,
    user_notification_preference_router,
)
from apps.api.v1.endpoints.store_rotations import (
    shop_item_router,
    shop_rotation_item_router,
    shop_rotation_router,
    shop_router,
)
from apps.api.v1.endpoints.tasks import sub_task_router, task_router
from apps.api.v1.endpoints.users import router as users_router
from apps.api.v1.endpoints.auth import router as auth_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(friends_router)
api_router.include_router(habits_router)
api_router.include_router(items_router)
api_router.include_router(achievement_router)
api_router.include_router(reward_router)
api_router.include_router(notification_router)
api_router.include_router(user_notification_preference_router)
api_router.include_router(shop_router)
api_router.include_router(shop_rotation_router)
api_router.include_router(shop_item_router)
api_router.include_router(shop_rotation_item_router)
api_router.include_router(task_router)
api_router.include_router(sub_task_router)
