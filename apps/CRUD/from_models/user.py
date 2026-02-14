from apps.CRUD.base import BaseCRUD
from apps.models.user import User
from apps.schemas.user import UserCreate, UserUpdate


class CRUDUser(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)


user_crud = CRUDUser()
