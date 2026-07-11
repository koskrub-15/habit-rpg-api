from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.store_rotation import (
    shop_item_crud,
    shop_rotation_crud,
    shop_rotation_item_crud,
)
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.store_rotation import (
    ShopItemCreate,
    ShopItemResponse,
    ShopItemResponseShort,
    ShopItemUpdate,
    ShopRotationCreate,
    ShopRotationItemCreate,
    ShopRotationItemResponse,
    ShopRotationItemResponseShort,
    ShopRotationItemUpdate,
    ShopRotationResponse,
    ShopRotationResponseShort,
    ShopRotationUpdate,
)

shop_rotation_factory = RouterFactory(
    crud=shop_rotation_crud,
    create_schema=ShopRotationCreate,
    update_schema=ShopRotationUpdate,
    response_schema=ShopRotationResponse,
    response_short_schema=ShopRotationResponseShort,
    resource_name="shop_rotation",
    resource_name_plural="shop_rotations",
    tag="Store",
    prefix="/shop_rotations",
    current_user_dependency=Depends(get_current_user),
)

shop_item_factory = RouterFactory(
    crud=shop_item_crud,
    create_schema=ShopItemCreate,
    update_schema=ShopItemUpdate,
    response_schema=ShopItemResponse,
    response_short_schema=ShopItemResponseShort,
    resource_name="shop_item",
    resource_name_plural="shop_items",
    tag="Store",
    prefix="/shop_items",
    current_user_dependency=Depends(get_current_user),
)

shop_rotation_item_factory = RouterFactory(
    crud=shop_rotation_item_crud,
    create_schema=ShopRotationItemCreate,
    update_schema=ShopRotationItemUpdate,
    response_schema=ShopRotationItemResponse,
    response_short_schema=ShopRotationItemResponseShort,
    resource_name="shop_rotation_item",
    resource_name_plural="shop_rotation_items",
    tag="Store",
    prefix="/shop_rotation_items",
    current_user_dependency=Depends(get_current_user),
)


shop_rotation_router = shop_rotation_factory.create_router()
shop_item_router = shop_item_factory.create_router()
shop_rotation_item_router = shop_rotation_item_factory.create_router()


shop_router = APIRouter(prefix="/shop", tags=["Shop"])


@shop_router.post("/buy/{shop_item_id}")
async def buy_item(
    shop_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buy an item from the shop."""
    return await user_crud.buy_item(db, current_user.id, shop_item_id)
