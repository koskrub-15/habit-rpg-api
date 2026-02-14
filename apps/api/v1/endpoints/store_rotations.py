from apps.CRUD.from_models.store_rotation import (
    shop_rotation_crud,
    shop_item_crud,
    shop_rotation_item_crud,
)
from apps.schemas.store_rotation import (
    ShopRotationCreate,
    ShopRotationUpdate,
    ShopRotationResponse,
    ShopRotationResponseShort,
    ShopItemCreate,
    ShopItemUpdate,
    ShopItemResponse,
    ShopItemResponseShort,
    ShopRotationItemCreate,
    ShopRotationItemUpdate,
    ShopRotationItemResponse,
    ShopRotationItemResponseShort,
)
from apps.api.router_generator import RouterFactory

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
)


shop_rotation_router = shop_rotation_factory.create_router()
shop_item_router = shop_item_factory.create_router()
shop_rotation_item_router = shop_rotation_item_factory.create_router()
