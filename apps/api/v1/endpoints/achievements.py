from fastapi import Depends

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.achievement import achievement_crud, reward_crud
from apps.schemas.achievement import (
    AchievementCreate,
    AchievementResponse,
    AchievementResponseShort,
    AchievementUpdate,
    RewardCreate,
    RewardResponse,
    RewardResponseShort,
    RewardUpdate,
)

achievement_factory = RouterFactory(
    crud=achievement_crud,
    create_schema=AchievementCreate,
    update_schema=AchievementUpdate,
    response_schema=AchievementResponse,
    response_short_schema=AchievementResponseShort,
    resource_name="achievement",
    resource_name_plural="achievements",
    tag="Achievements",
    prefix="/achievements",
    current_user_dependency=Depends(get_current_user),
    write_requires_superuser=True,
)

reward_factory = RouterFactory(
    crud=reward_crud,
    create_schema=RewardCreate,
    update_schema=RewardUpdate,
    response_schema=RewardResponse,
    response_short_schema=RewardResponseShort,
    resource_name="reward",
    resource_name_plural="rewards",
    tag="Achievements",
    prefix="/rewards",
    current_user_dependency=Depends(get_current_user),
    write_requires_superuser=True,
)

achievement_router = achievement_factory.create_router()
reward_router = reward_factory.create_router()
