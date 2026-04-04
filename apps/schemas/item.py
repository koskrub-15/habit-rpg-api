from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse
from apps.models.item import ItemTheme, ItemType, Rarity

if TYPE_CHECKING:
    from apps.schemas.achievement import RewardResponseShort
    from apps.schemas.store_rotation import ShopItemResponseShort
    from apps.schemas.user import UserResponseShort


class ItemCreate(BaseSchemaCreate):
    item_type: ItemType
    defense: Optional[int] = 0
    attack: Optional[int] = 0
    pet_power: Optional[int] = 0
    required_level: Optional[int] = 0
    rarity: Optional[Rarity] = Rarity.COMMON
    available_in_shop: Optional[bool] = False
    theme: Optional[ItemTheme] = ItemTheme.COMMON


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    defense: Optional[int] = None
    attack: Optional[int] = None
    pet_power: Optional[int] = None
    required_level: Optional[int] = None
    rarity: Optional[Rarity] = None
    available_in_shop: Optional[bool] = None
    theme: Optional[ItemTheme] = None
    item_type: Optional[ItemType] = None


class ItemResponseShort(BaseSchemaResponse):
    description: str
    item_type: ItemType

    rarity: Optional[Rarity] = None


class ItemResponse(ItemResponseShort):
    defense: Optional[int] = None
    attack: Optional[int] = None
    pet_power: Optional[int] = None
    required_level: Optional[int] = None
    rarity: Optional[Rarity] = None
    available_in_shop: Optional[bool] = None
    theme: Optional[ItemTheme] = None
    rewards: List["RewardResponseShort"] = []
    shop_items: List["ShopItemResponseShort"] = []


class ItemResponseFull(ItemResponse):
    users: List["UserResponseShort"] = []
