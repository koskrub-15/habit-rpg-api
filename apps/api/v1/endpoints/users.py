from apps.CRUD.from_models.user import user_crud
from apps.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserResponseShort,
)
from apps.api.router_generator import RouterFactory

user_factory = RouterFactory(
    crud=user_crud,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    response_schema=UserResponse,
    response_short_schema=UserResponseShort,
    resource_name="user",
    resource_name_plural="users",
    tag="Users",
    prefix="/users",
)

router = user_factory.create_router()
