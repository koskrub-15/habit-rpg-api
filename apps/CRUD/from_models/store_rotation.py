from apps.CRUD.base import BaseCRUD
from apps.models.store_rotation import ShopItem, ShopRotation, ShopRotationItem
from apps.schemas.store_rotation import (
    ShopItemCreate,
    ShopItemUpdate,
    ShopRotationCreate,
    ShopRotationItemCreate,
    ShopRotationItemUpdate,
    ShopRotationUpdate,
)


class CRUDShopItem(BaseCRUD[ShopItem, ShopItemCreate, ShopItemUpdate]):
    def __init__(self):
        super().__init__(model=ShopItem)


class CRUDShopRotation(BaseCRUD[ShopRotation, ShopRotationCreate, ShopRotationUpdate]):
    def __init__(self):
        super().__init__(model=ShopRotation)


class CRUDShopRotationItem(
    BaseCRUD[ShopRotationItem, ShopRotationItemCreate, ShopRotationItemUpdate]
):
    def __init__(self):
        super().__init__(model=ShopRotationItem)


shop_item_crud = CRUDShopItem()
shop_rotation_crud = CRUDShopRotation()
shop_rotation_item_crud = CRUDShopRotationItem()
