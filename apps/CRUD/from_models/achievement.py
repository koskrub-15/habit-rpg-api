from apps.CRUD.base import BaseCRUD
from apps.models.achievement import Achievement, Reward
from apps.schemas.achievement import (
    AchievementCreate,
    AchievementUpdate,
    RewardCreate,
    RewardUpdate,
)


class CRUDAchievement(BaseCRUD[Achievement, AchievementCreate, AchievementUpdate]):
    def __init__(self):
        super().__init__(model=Achievement)


class CRUDReward(BaseCRUD[Reward, RewardCreate, RewardUpdate]):
    def __init__(self):
        super().__init__(model=Reward)


achievement_crud = CRUDAchievement()
reward_crud = CRUDReward()
