from apps.CRUD.base import BaseCRUD
from apps.models.boss import Boss
from apps.schemas.boss import BossCreate, BossUpdate


class CRUDBoss(BaseCRUD[Boss, BossCreate, BossUpdate]):
    def __init__(self):
        super().__init__(model=Boss)


boss_crud = CRUDBoss()
