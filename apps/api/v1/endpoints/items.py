from fastapi import Depends

from apps.api.deps import get_current_user
from apps.CRUD.from_models.item import item_crud
from apps.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemResponseShort,
)
from apps.api.router_generator import RouterFactory

item_factory = RouterFactory(
    crud=item_crud,
    create_schema=ItemCreate,
    update_schema=ItemUpdate,
    response_schema=ItemResponse,
    response_short_schema=ItemResponseShort,
    resource_name="item",
    resource_name_plural="items",
    tag="Items",
    prefix="/items",
    current_user_dependency=Depends(get_current_user),
)

router = item_factory.create_router()
